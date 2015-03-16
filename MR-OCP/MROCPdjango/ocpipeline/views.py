#!/usr/bin/env python

# Copyright 2014 Open Connectome Project (http://openconnecto.me)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
@author : Disa Mhembere
@organization: Johns Hopkins University
@contact: disa@jhu.edu

@summary: Module to hold the views of a Django one-click MR-connectome pipeline
"""
import os, sys, re
from glob import glob
import threading
from random import randint
os.environ["MPLCONFIGDIR"] = "/tmp/"

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from django.core.files import File        # For programmatic file upload

# Model & Form imports
#from models import BuildGraphModel
from models import OwnedProjects

from forms import DownloadForm
from forms import GraphUploadForm
from forms import ConvertForm
from forms import PasswordResetForm

## Data Processing imports ##
import paths
from mrcap import gengraph as gengraph
from mrcap.utils import igraph_io

from  utils.filesorter import checkFileExtGengraph
import utils.zipper as zipper
from utils.create_dir_struct import create_dir_struct
from computation.utils.convertTo import convert_graph

from django.core.servers.basehttp import FileWrapper

import subprocess
from django.core.urlresolvers import get_script_prefix
from django.conf import settings

from time import strftime, localtime
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import redirect

## Graph Analysis imports ##
import computation.composite.invariants as cci
import scipy.io as sio
from nibabel import load as nib_load

## Auth imports ##
from django.contrib.auth.decorators import login_required

# Registration
from django.contrib.auth import authenticate, login, logout

# Helpers
from utils.util import *

def default(request):
  """ Base url just redirects to welcome """
  return redirect(get_script_prefix()+"welcome", {"user":request.user})

def welcome(request):
  """ Little welcome message """
  return render_to_response("welcome.html", {"user":request.user},
                            context_instance=RequestContext(request))

def success(request):
  """ Successful completion of task"""
  return render_to_response("success.html", {"msg": request.session["success_msg"]}
                            ,context_instance=RequestContext(request))

def jobfailure(request):
  """ Job failure """
  return render_to_response("job_failure.html", {"msg": "Please check that your fiber streamline file and ROI's are correctly formatted"}
                            ,context_instance=RequestContext(request))

def getRootUrl(request):
  return request.META['wsgi.url_scheme'] + '://' + request.META['HTTP_HOST']

@login_required
def showdir(request):
  #directory = request.session['usrDefProjDir']
  return render('STUB')

def contact(request):
  return render_to_response('contact.html', context_instance=RequestContext(request))

def igraph_examples(request):
  return render_to_response("igraph_examples.html", context_instance=RequestContext(request))

def human_data_descrip(request):
  return render_to_response("human_data_descrip.html", context_instance=RequestContext(request))

def upload(request, webargs=None):
  """
  Programmatic interface for uploading data
  @param request: the request object

  @param webargs: POST data with userDefProjectName, site, subject, session,
        scanId, graphsize, [list of invariants to compute] info
  """
  if (webargs and request.method == 'POST'):
    # Check for malformatted input
    webargs = webargs[1:] if webargs.startswith('/') else webargs
    webargs = webargs[:-1] if webargs.endswith('/') else webargs

    if len(webargs.split('/')) == 7:
      [userDefProjectName, site, subject, session, scanId, graphsize, request.session['invariants']] = webargs.split('/')

      request.session['invariants'] = request.session['invariants'].split(',')
    elif len(webargs.split('/')) == 6:
      [userDefProjectName, site, subject, session, scanId, graphsize] = webargs.split('/')
    else:
      # Some sort of error
      return HttpResponseBadRequest ("Malformatted programmatic request. Check format of url and data requests")

    userDefProjectDir = adaptProjNameIfReq(os.path.join(settings.MEDIA_ROOT, 'public', userDefProjectName, site, subject, session, scanId))

    ''' Define data directory paths '''
    derivatives, graphs, request.session['graphInvariants'] = defDataDirs(userDefProjectDir)

    ''' Make appropriate dirs if they dont already exist '''
    create_dir_struct([derivatives, graphs,request.session["graphInvariants"]])
    print 'Directory structure created...'

    uploadFiles =  writeBodyToDisk(request.body, derivatives)

    # Check which file is which
    fiber_fn, data_atlas_fn = checkFileExtGengraph(uploadFiles) # Check & sort files
    if not data_atlas_fn:
      data_atlas_fn = settings.ATLASES.keys()[0]
    else:
      data_atlas_fn = os.path.join(derivatives, data_atlas_fn)

    ''' Data Processing '''
    if graphsize:
      request.session['Gfn']= call_gengraph(fiber_fn, data_atlas_fn, \
                              graphs, request.session['graphInvariants'],\
                              graphsize, run=True)

    else:
      return HttpResponseBadRequest ("Missing graph size. You must specify big or small")


    # Run invariants
    if request.session.has_key('invariants'):
      print "Computing invariants ..."

      invariant_fns = run_invariants(request.session['invariants'],\
                      request.session['Gfn'], request.session['graphInvariants'])

    #dwnldLoc = request.META['wsgi.url_scheme'] + '://' + \
                    #request.META['HTTP_HOST'] + userDefProjectDir.replace(' ','%20')
    dwnldLoc = "http://mrbrain.cs.jhu.edu" + userDefProjectDir.replace(' ','%20')

    return HttpResponse ( "Files available for download at " + dwnldLoc) # change to render of a page with a link to data result

  elif(not webargs):
    return HttpResponseBadRequest ("Expected web arguments to direct project correctly")

  else:
    return HttpResponseBadRequest ("Expected POST data, but none given")


######################################################


#########################################
#	*******************		#
#	  CONVERT GRAPH FORMAT		#
#########################################

def convert(request, webargs=None):
  """ Browser """
  if (request.method == 'POST' and not webargs):
    form = ConvertForm(request.POST, request.FILES) # instantiating form
    if form.is_valid():

      baseDir = os.path.join(settings.MEDIA_ROOT, 'tmp', strftime('formUpload%a%d%b%Y_%H.%M.%S/', localtime()))
      saveDir = os.path.join(baseDir,'upload') # Save location of original uploads
      convertFileSaveLoc = os.path.join(baseDir,'converted') # Save location of converted data

      if not (os.path.exists(convertFileSaveLoc)):
        os.makedirs(convertFileSaveLoc)

      savedFile = os.path.join(saveDir, request.FILES['fileObj'].name)

      saveFileToDisk(request.FILES['fileObj'], savedFile)

      # If zip is uploaded
      if os.path.splitext(request.FILES['fileObj'].name)[1].strip() == '.zip':
        zipper.unzip(savedFile, saveDir)
        # Delete zip so its not included in the graphs we uploaded
        os.remove(savedFile)
        uploadedFiles = glob(os.path.join(saveDir, "*")) # get the uploaded file names

      else:
        uploadedFiles = [savedFile]

      err_msg = ""
      outfn = ""
      for fn in uploadedFiles:
        outfn, err_msg = convert_graph(fn, form.cleaned_data['input_format'],
                        convertFileSaveLoc, *form.cleaned_data['output_format'])

      #dwnldLoc = request.META['wsgi.url_scheme'] + '://' + \
      #              request.META['HTTP_HOST'] + convertFileSaveLoc.replace(' ','%20')

      dwnldLoc = "http://mrbrain.cs.jhu.edu" + convertFileSaveLoc.replace(' ','%20')

      if (err_msg):
        err_msg = "Your job completed with errors. The result can be found <a href=\"%s\" target=\"blank\">here</a>.<br> Message %s" % (dwnldLoc, err_msg)
        return render_to_response(
        'convertupload.html',
        {'convertForm': form, 'err_msg': err_msg+"\n"},
        context_instance=RequestContext(request))
      #else
      return HttpResponseRedirect(dwnldLoc)

  elif(request.method == 'POST' and webargs):
    # webargs is {inFormat}/{outFormat}
    inFormat = webargs.split('/')[0] # E.g 'graphml'| 'dot' | 'leda'
    outFormat =  webargs.split('/')[1].split(',')

    outFormat = list(set(outFormat)) # Eliminate duplicates if any exist

    baseDir = os.path.join(settings.MEDIA_ROOT, 'tmp', strftime('progUpload%a%d%b%Y_%H.%M.%S/', localtime()))
    saveDir = os.path.join(baseDir,'upload') # Save location of original uploads
    convertFileSaveLoc = os.path.join(baseDir,'converted') # Save location of converted data

    if not os.path.exists(saveDir): os.makedirs(saveDir)
    if not os.path.exists(convertFileSaveLoc): os.makedirs(convertFileSaveLoc)

    uploadedFiles = writeBodyToDisk(request.body, saveDir)# can only be one file # TODO: Check me

    # Check for zip
    if os.path.splitext(uploadedFiles[0])[1].strip() == '.zip':
        zipper.unzip(uploadedFiles[0], saveDir)
        # Delete zip so its not included in the graphs we uploaded
        os.remove(uploadedFiles[0])
        uploadedFiles = glob(os.path.join(saveDir, "*")) # get the uploaded file names

    err_msg = ""
    outfn = ""
    for fn in uploadedFiles:
      outfn, err_msg = convert_graph(fn, inFormat,
                        convertFileSaveLoc, *outFormat)

    dwnldLoc = "http://mrbrain.cs.jhu.edu" + convertFileSaveLoc.replace(' ','%20')

    if err_msg:
      err_msg = "Completed with errors. View Data at: %s\n. Here are the errors:%s" % (dwnldLoc, err_msg)
      return HttpResponse(err_msg)

    elif len(webargs.split("/")) > 2:
      if (outfn and len(outFormat) == 1):
        return HttpResponse(dwnldLoc + "/" + outfn.split("/")[-1])
      else:
        return HttpResponse(dwnldLoc)

    return HttpResponse ("Converted files available for download at " + dwnldLoc + " . The directory " +
            "may be empty if you try to convert from, and to the same format.") # change to render of a page with a link to data result

  else:
    form = ConvertForm() # An empty, unbound form

  # Render the form
  return render_to_response(
      'convertupload.html',
      {'convertForm': form},
      context_instance=RequestContext(request))

#########################################
#	*******************		#
#	   PROCESS DATA			#
#########################################

def call_gengraph(fiber_fn, data_atlas_fn, graphs, graphInvariants, graphsize, run = False):
  '''
  Run graph building and other related scripts
  @param fiber_fn: fiber tract file
  @param data_atlas_fn: the data atlas defining ROIs and region

  @param graphs: Dir where biggraphs & smallgraphs are saved
  @param graphInvariants:  Dir where graph invariants are saved
  @param graphsize: the size of the graph 'big' or 'small'
  @param run: Whether or not to run processor intensive jobs. Default is - false so nothing is actually run
  '''

  baseName = getFiberID(fiber_fn) #VERY TEMPORARY

  Gfn = os.path.join(graphs, baseName) # partial name

  if (run):
    if graphsize.lower().startswith("s"):
      print("Running Small gengraph ...")
      Gfn+="smgr.graphml"

      # Note: Some included atlases are present
      gengraph.genGraph(fiber_fn, data_atlas_fn, Gfn, bigGraph=False, **settings.ATLASES)

    elif graphsize.lower().startswith("b"):
      print("\nRunning Big gengraph ...")
      Gfn+="bggr.graphml"
      gengraph.genGraph(fiber_fn, data_atlas_fn, Gfn, bigGraph=True, **settings.ATLASES)
    else:
      print '[ERROR]: Graphsize Unkwown' # should never happen
  return Gfn


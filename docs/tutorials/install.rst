******************
Install
******************

.. contents:: Table of Contents


Summary
===================

Pull docker container::

    docker pull neurodata/m3r-release:0.1.1

Run dmri participant pipeline::

    docker run -ti -v </path/local/to/data>:/inputs -v </path/local/out>:/outputs neurodata/m3r-release:0.1.1 /inputs /outputs participant dwi --nproc <ncores>

System Requirements
====================
.. TODO: update package versions

The ndmg pipeline:

- was developed and tested primarily on Mac OSX, Ubuntu (12, 14, 16), and CentOS (5, 6);
- was developed in Python 2.7;
- is wrapped in a Docker container;
- has install instructions via a Dockerfile;
- requires no non-standard hardware to run;
- has key features built upon FSL, Dipy, Nibabel, Nilearn, Networkx, Numpy, Scipy, Scikit-Learn, and others;
- takes approximately 1-core, 8-GB of RAM, and 1 hour to run for most datasets.
- While ndmg is quite robust to Python package versions (with only few exceptions, mentioned in the installation guide), an example of possible versions (taken from the ndmg Docker Image with version v0.0.50) is shown below. Note: this list excludes many libraries which are standard with a Python distribution, and a complete list with all packages and versions can be produced by running ``pip freeze`` within the Docker container mentioned above. ::

    awscli==1.11.128 , boto3==1.4.5 , botocore==1.5.91 , colorama==0.3.7 , dipy==0.12.0 , matplotlib==1.5.1 ,
    networkx==1.11 , nibabel==2.1.0 , nilearn==0.3.1 , numpy==1.8.2 , Pillow==2.3.0 , plotly==1.12.9 ,
    s3transfer==0.1.10 , scikit-image==0.13.0 , scikit-learn==0.18.2 , scipy==0.13.3 .

Installation Guide
==================
.. TODO: add links to external packages

Currently, the Docker image is recommended. 

``pip`` and Github installations are also available.

Docker
--------------
.. _Dockerhub : https://hub.docker.com/r/neurodata/m3r-release/
.. _documentation : https://docs.docker.com/

The neurodata/m3r-release Docker container enables users to run end-to-end connectome estimation on structural MRI or functional MRI right from container launch. The pipeline requires that data be organized in accordance with the BIDS spec. If the data you wish to process is available on S3 you simply need to provide your s3 credentials at build time and the pipeline will auto-retrieve your data for processing.

If you have never used Docker before, it is useful to run through the Docker documentation_.

**Getting Docker container**::

    $ docker pull neurodata/m3r-release

*(A) I do not wish to use S3:*

You are good to go!

*(B) I wish to use S3:*

Add your secret key/access id to a file called credentials.csv in this directory on your local machine. A dummy file has been provided to make the format we expect clear. (This is how AWS provides credentials)

**Processing Data**

Below is the help output generated by running **ndmg** with the ``-h`` command. All parameters are explained in this output. ::

    $ docker run -ti neurodata/m3r-release -h

    usage: ndmg_bids [-h]
                    [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]]
                    [--session_label SESSION_LABEL [SESSION_LABEL ...]]
                    [--task_label TASK_LABEL [TASK_LABEL ...]]
                    [--run_label RUN_LABEL [RUN_LABEL ...]] [--bucket BUCKET]
                    [--remote_path REMOTE_PATH] [--push_data] [--dataset DATASET]
                    [--atlas ATLAS] [--minimal] [--hemispheres] [--log] [--debug]
                    [--bg BG] [--nthreads NTHREADS] [--stc STC]

    This is an end-to-end connectome estimation pipeline from M3r images

    positional arguments:
    bids_dir              The directory with the input dataset formatted
                            according to the BIDS standard.
    output_dir            The directory where the output files should be stored.
                            If you are running group level analysis this folder
                            should be prepopulated with the results of the
                            participant level analysis.
    {participant,group}   Level of the analysis that will be performed. Multiple
                            participant level analyses can be run independently
                            (in parallel) using the same output_dir.
    {dwi,func}            Modality of MRI scans that are being evaluated.

    optional arguments:
    -h, --help            show this help message and exit
    --participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]
                            The label(s) of the participant(s) that should be
                            analyzed. The label corresponds to
                            sub-<participant_label> from the BIDS spec (so it does
                            not include "sub-"). If this parameter is not provided
                            all subjects should be analyzed. Multiple participants
                            can be specified with a space separated list.
    --session_label SESSION_LABEL [SESSION_LABEL ...]
                            The label(s) of the session that should be analyzed.
                            The label corresponds to ses-<participant_label> from
                            the BIDS spec (so it does not include "ses-"). If this
                            parameter is not provided all sessions should be
                            analyzed. Multiple sessions can be specified with a
                            space separated list.
    --task_label TASK_LABEL [TASK_LABEL ...]
                            The label(s) of the task that should be analyzed. The
                            label corresponds to task-<task_label> from the BIDS
                            spec (so it does not include "task-"). If this
                            parameter is not provided all tasks should be
                            analyzed. Multiple tasks can be specified with a space
                            separated list.
    --run_label RUN_LABEL [RUN_LABEL ...]
                            The label(s) of the run that should be analyzed. The
                            label corresponds to run-<run_label> from the BIDS
                            spec (so it does not include "task-"). If this
                            parameter is not provided all runs should be analyzed.
                            Multiple runs can be specified with a space separated
                            list.
    --bucket BUCKET       The name of an S3 bucket which holds BIDS organized
                            data. You must have built your bucket with credentials
                            to the S3 bucket you wish to access.
    --remote_path REMOTE_PATH
                            The path to the data on your S3 bucket. The data will
                            be downloaded to the provided bids_dir on your
                            machine.
    --push_data           flag to push derivatives back up to S3.
    --dataset DATASET     The name of the dataset you are perfoming QC on.
    --atlas ATLAS         The atlas being analyzed in QC (if you only want one).
    --minimal             Determines whether to show a minimal or full set of
                            plots.
    --hemispheres         Whether or not to break degrees into hemispheres or
                            not
    --log                 Determines axis scale for plotting.
    --debug               flag to store temp files along the path of processing.
    --bg BG               Whether to produce big graphs.
    --nthreads NTHREADS   The number of threads you have available. Should be
                            approximately min(ncpu*hyperthreads/cpu, maxram/10).
    --stc STC             A file for slice timing correction. Options are a TR
                            sequence file (where each line is the shift in TRs),
                            up (ie, bottom to top), down (ie, top to bottom), and
                            interleaved.

In order to share data between our container and the rest of our machine in Docker, we need to mount a volume. Docker does this with the -v flag. Docker expects its input formatted as: ``-v path/to/local/data:/path/in/container``. We'll do this when we launch our container, as well as give it a helpful name so we can locate it later on.

**To run ndmg on data** ::

    docker run -ti -v </path/local/to/data>:/inputs -v </path/local/out>:/outputs neurodata/m3r-release:0.1.1 /inputs /outputs participant dwi

If you have a computer with multiple cores, using the ``--nproc`` flag is highly recommended for parallel processing.

Pip
-------------

ndmg relies on FSL, Dipy, networkx, and nibabel, numpy scipy, scikit-learn, scikit-image, nilearn. You should install FSL through the instructions on their website, then follow install other Python dependencies with the following::

    pip install ndmg

The only known packages which require a specific version are plotly and networkx, due to backwards-compatability breaking changes.

Installation shouldn't take more than a few minutes, but depends on your internet connection.

Github
-----------

To install directly from Github, run::

    git clone https://github.com/neurodata/ndmg
    cd ndmg
    python setup.py install
#!/usr/bin/env python

# Copyright 2016 NeuroData (http://neurodata.io)
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

# graph.py
# Created by Greg Kiar on 2016-01-27.
# Email: gkiar@jhu.edu

from __future__ import print_function
import warnings
warnings.simplefilter("ignore")
from itertools import combinations, product
from collections import defaultdict
import numpy as np
import networkx as nx
import nibabel as nb
import ndmg
import time

class graph_tools(object):
    def __init__(self, rois, tracks, attr=None, sens="dwi"):
        """
        Initializes the graph with nodes corresponding to the number of ROIs

        **Positional Arguments:**
                rois:
                    - Set of ROIs as either an array or niftii file)
                attr:
                    - Node or graph attributes. Can be a list. If 1 dimensional
                      will be interpretted as a graph attribute. If N
                      dimensional will be interpretted as node attributes. If
                      it is any other dimensional, it will be ignored.
                sens: string, Default to 'dmri'
                    - sensor of acquisition. Can be 'dmri' or 'fmri'
        """
        self.edge_dict = defaultdict(int)
	self.roi_img = nb.load(rois)
        self.rois = roi_img.get_data().astype('int')
        n_ids = np.unique(self.rois)
        self.n_ids = n_ids[n_ids > 0]
        self.N = len(self.n_ids)
        self.modal = sens
	self.tracks = tracks
        pass

    def make_graph(self, attr=None):
        """
        Takes streamlines and produces a graph. Note that the parcellation is
        expected to be numbered from 0 to n, where n are the number of vertices.
        If any vertices are skipped, non-deterministic behavior may be expected.

        **Positional Arguments:**

                tracks:
                    - Fiber streamlines either file or array in a dipy EuDX
                      or compatible format.
        """
	from dipy.tracking import utils
	conn_matrix, grouping = utils.connectivity_matrix(self.tracks, self.rois, affine=roi_img.affine, return_mapping=True, mapping_as_streamlines=True)
	conn_matrix = np.divide(conn_matrix, conn_matrix.sum(axis=0))
	conn_matrix[np.isnan(conn_matrix)] = 0
	conn_matrix[np.isinf(conn_matrix)] = 0
        self.g = nx.Graph(nx.from_numpy_matrix(conn_matrix), name="Generated by NeuroData's MRI Graphs (ndmg)",
                          date=time.asctime(time.localtime()),
                          source="http://m2g.io",
                          region="brain",
                          sensor=self.modal,
                          ecount=0,
                          vcount=len(self.n_ids)
                          )
        print(self.g.graph)
        return self.g

    def cor_graph(self, timeseries, attr=None):
        """
        Takes timeseries and produces a correlation matrix

        **Positional Arguments:**
            timeseries:
                -the timeseries file to extract correlation for
                dimensions are [numrois]x[numtimesteps]
        """
        ts = timeseries[0]
        rois = timeseries[1]
        print("Estimating absolute correlation matrix for {} ROIs...".format(len(rois)))
        self.g = np.abs(np.corrcoef(ts))  # calculate abs pearson correlation
        self.g = np.nan_to_num(self.g).astype(object)
        self.n_ids = rois
        return self.g        

    def get_graph(self):
        """
        Returns the graph object created
        """
        try:
            return self.g
        except AttributeError:
            print("Error: the graph has not yet been defined.")
            pass

    def as_matrix(self):
        """
        Returns the graph as a matrix.
        """
        g = self.get_graph()
        return nx.to_numpy_matrix(g, nodelist=np.sort(g.nodes()).tolist())

    def save_graph(self, graphname, fmt='igraph'):
        """
        Saves the graph to disk

        **Positional Arguments:**

                graphname:
                    - Filename for the graph
        """
        self.g.graph['ecount'] = nx.number_of_edges(self.g)
        self.g = nx.convert_node_labels_to_integers(self.g, first_label=1)
        if fmt == 'edgelist':
            nx.write_weighted_edgelist(self.g, graphname, encoding='utf-8')
        elif fmt == 'gpickle':
            nx.write_gpickle(self.g, graphname)
        elif fmt == 'graphml':
            nx.write_graphml(self.g, graphname)
	elif fmt == 'txt':
	    np.savetxt(graphname, nx.to_numpy_matrix(self.g))
        elif fmt == 'npy':
            np.save(graphname, nx.to_numpy_matrix(self.g))
	elif fmt == 'igraph':
	    if self.modal == 'dwi':
                nx.write_weighted_edgelist(self.g, graphname, delimiter=" ", encoding='utf-8')
            elif self.modal == 'func':
                np.savetxt(graphname, self.g, comments='', delimiter=',', header=','.join([str(n) for n in self.n_ids]))
            else:
                raise ValueError("Unsupported Modality.")
        else:
            raise ValueError('Only edgelist, gpickle, and graphml currently supported')
        pass

    def summary(self):
        """
        User friendly wrapping and display of graph properties
        """
        print("\nGraph Summary:")
        print(nx.info(self.g))
        pass

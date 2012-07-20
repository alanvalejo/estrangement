#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This module implements various functions used to compute and plot temporal communities.
"""

__all__ = ['graph_distance','node_graph_distance','Estrangement','match_labels','confidence_interval']

__author__ = """\n""".join(['Vikas Kawadia (vkawadia@bbn.com)',
                            'Sameet Sreenivasan <sreens@rpi.edu>',
                            'Stephen Dabideen <dabideen@bbn.com>'])

#   Copyright (C) 2012 by 
#   Vikas Kawadia <vkawadia@bbn.com>
#   Sameet Sreenivasan <sreens@rpi.edu>
#   Stephen Dabideen <dabideen@bbn.com>
#   All rights reserved. 
#   BSD license. 

import networkx as nx
import collections
import math
import operator
import numpy
import logging

def graph_distance(g0, g1, weighted=True):

    """Function to calculate and return the Tanimoto distance between the two input graphs.

    Let **a** be the set of edges belonging to graph *G0* and let **b** be the set of
    edges belonging to *G1*. The Tanimoto distance between *G0* and *G1* is defined as    
    (aUb - a.b)/aUb where a.b is dot product and aUb = a^2 + b^2 - a.b

    Parameters
    ----------
    g0,g1: networkx.Graph
        The networkx graphs to be compared.
    weighted: boolean
        True if the edges of the graph are weighted, False otherwise.

    Returns
    -------
    graph_distance: float
        The Tanimoto distance between the nodes of g0 and g1.

    Examples
    --------
    >>> g0 = nx.complete_graph(5)
    >>> g1 = nx.complete_graph(5)
    >>> print(graph_distance(g0,g1,False)
    0
    """

    intersection = set(g1.edges_iter()) & set(g0.edges_iter())
    if weighted is False:
        union = set(g1.edges_iter()) | set(g0.edges_iter())
        graph_distance = (len(union) - len(intersection))/float(len(union))
    else:
        g0weights = nx.get_edge_attributes(g0,'weight')
        g1weights = nx.get_edge_attributes(g1,'weight')
        dot_product = sum((g0weights[i]*g1weights[i] for i in intersection))
        e1_norm = sum((g1weights[i]**2 for i in g1.edges_iter()))
        e0_norm = sum((g0weights[i]**2 for i in g0.edges_iter()))
        graph_distance = 1 - dot_product/float(e0_norm + e1_norm - dot_product)

    return graph_distance

def node_graph_distance(g0, g1):

    """Function to calculate and return the Jaccard distance between the two input graphs.

    Let **a** be the set of nodes belonging to graph *G0* and let **b** be the set of 
    nodes belonging to *G1*. The Jaccard distance between *G0* and *G1* is defined as    
    (a.b - (aUb - a.b)) /aUb where a.b is dot product and aUb = a^2 + b^2 - a.b

    Parameters
    ----------
    g0,g1: networkx.Graph
        The networkx graphs to be compared.

    Returns
    -------
    node_graph_distance: float
        The Jaccard distance between the nodes of g0 and g1.
        
    Examples
    --------
    >>> g0 = nx.path_graph(2)
    >>> g1 = nx.path_graph(4)
    >>> print(node_graph_distance(g0,g1)
    0.5
    """

    g1_nodes = set(g1.nodes())
    g0_nodes = set(g0.nodes())
    graph_distance = 1 - len(g0_nodes & g1_nodes)/float(len(g0_nodes | g1_nodes)) 
    
    return graph_distance

def Estrangement(G, label_dict, Zgraph):

    """Return the Estrangement between G and Zgraph

    Given network snapshots and partitioning at times *t* and *(t-1)*, 
    an edge (u; v) in |Gt| is said to be estranged if, *u* and *v* are
    in the same partition in |G(t-1)| but not in |Gt|.
    Estrangement is defined as the fraction of estranged edges in G\ :sub:`t` \.

    .. |Gt| replace:: G\ :sub:`t`
    .. |G(t-1)| replace:: G\ :sub:`t-1`

    Parameters
    -----------
    G: networkx.Graph
        A networkx graph object representing the current snapshot.
    label_dict: dictionary {node:community}
        A dictionary mapping nodes to communities.
    Zgraph: networkx.Graph
        A graph containing only the edges between nodes of the same community in all previous snapshots.
  
    Returns
    -------
    estrangement: float
	The weighted fraction of estranged edges in *G*. 
 
    See Also
    --------
    lpa.lpa
    agglomerate.generate_dendogram()

    Examples
    --------
    >>> g0 = nx.Graph()
    >>> g0.add_edges_from([(1,2,{'weight':2}),(1,3,{'weight':1}),(2,3,{'weight':1})])
    >>> g1.add_edges_from([(1,2,{'weight':2})])
    >>> communities = {1:'a',2:'a',3:'b'}
    >>> print(Estrangement(g0,communities,g1)
    0.333333333333
    """

    consort_edge_set =  set(Zgraph.edges()) & set(G.edges())
    logging.info("Estrangement(): Z edges: %s", str(Zgraph.edges(data=True)))   
    logging.info("Estrangement(): G edges: %s", str(G.edges(data=True)))   
    logging.info("Estrangement(): consort_edge_set: %s", str(consort_edge_set))   
    if len(consort_edge_set) == 0:
        estrangement = 0
    else:   
        estrangement = sum([e[2]['weight'] for e in Zgraph.edges(data=True) if label_dict[e[0]] !=
        label_dict[e[1]]]) / float(G.size(weight='weight'))
    return estrangement


def match_labels(label_dict, prev_label_dict):

    """Returns a list of community labels to be preserved, representing the 
    communities that remain mostly intact between snapshots.

    We start by representing the communities at time *t-1* and at time *t* as 
    nodes of a bipartite graph. From each node at time *t-1*, we  draw a directed 
    link to the node at time *t* with which it has maximum overlap. From each node 
    at time *t*, we  draw a directed link to the node at time *t-1* with which it 
    has maximum overlap.

    Basically x,y and z choose who they are most similar to among a and b
    and denote this by arrows directed outward from them. Similarly a and
    b, choose who they are most similar to among x, y and z. Then the rule
    is that labels on the t-1 side of every bidirected (symmetric) link is
    preserved - all other labels on the t-1 side are removed.

    Parameters
    ----------
    label_dict: dictionary
        {node:community} at time t.
    prev_label_dict: dictionary
        {node:community} at time (t - 1).

    Returns
    -------
    matched_label_dict: dictionary {node:community} 
        The new community labelling.

    Examples
    --------
    >>> label_dict_a = {1:'a',2:'a',3:'a',4:'a',5:'a',6:'a'}
    >>> label_dict_b = {1:'b',2:'b',3:'b',4:'b',5:'b',6:'b'}
    >>> print(match_labels(label_dict_a,label_dict_b)
    {1:'a',2:'a',3:'a',4:'a',5:'a',6:'a'}
    """
    
    # corner case for the first snapshot
    if prev_label_dict == {}:
        return label_dict

    nodesets_per_label_t = collections.defaultdict(set) 
    nodesets_per_label_t_minus_1 = collections.defaultdict(set) 

    # count the number of nodes with each label in each snapshot and store in a dictionary
    # key = label, val = set of nodes with that label 
    for n,l in label_dict.items():
        nodesets_per_label_t[l].add(n)

    for n,l in prev_label_dict.items():
        nodesets_per_label_t_minus_1[l].add(n)

    overlap_dict = {} 
    overlap_graph = nx.Graph() 
    # Undirected bi-partite graph with the vertices being the labels and
    # the weight being the jaccard distance between them in t and (t-1) 
    # key = (prev_label, new_label), value = jaccard overlap

    for l_t, nodeset_t in nodesets_per_label_t.items():
        for l_t_minus_1, nodeset_t_minus_1 in nodesets_per_label_t_minus_1.items():
            jaccard =  len(nodeset_t_minus_1 & nodeset_t)/float(len((nodeset_t_minus_1 | nodeset_t))) 
            overlap_graph.add_edge(l_t_minus_1, l_t, weight=jaccard)

    max_overlap_digraph = nx.DiGraph() 
    # each label at t-1  and at t is a vertex in this bi-partite graph and 
    # a directed edge implies the max overlap with the other side. 

    for v in overlap_graph.nodes():    # find the nbr with max weight
        maxwt_nbr = max([(nbrs[0],nbrs[1]['weight']) for nbrs in overlap_graph[v].items()],
            key=operator.itemgetter(1))[0]
        max_overlap_digraph.add_edge(v, maxwt_nbr)

    matched_label_dict = {} # key = node, value = new label
    for l_t in nodesets_per_label_t.keys():
        match_l_t_minus_1 = max_overlap_digraph.successors(l_t)[0]
        # match if it is a bi-directional edge
        if max_overlap_digraph.successors(match_l_t_minus_1)[0] == l_t:
            best_matched_label = match_l_t_minus_1
        else:
            best_matched_label = l_t

        for n in nodesets_per_label_t[l_t]:
            matched_label_dict[n] = best_matched_label

    return matched_label_dict

def confidence_interval(nums):

    """Return (half) the 95% confidence interval around the mean for the list of input numbers,
    i.e. calculate: 1.96 * std_deviation / sqrt(len(nums)).
    
    Parameters
    ----------
    nums: list of floats

    Returns
    -------
    half the range of the 95% confidence interval

    Examples
    --------
    >>> print(confidence_interval([2,2,2,2]))
    0
    >>> print(confidence_interval([2,2,4,4]))
    0.98
    """

    return 1.96 * numpy.std(nums) / math.sqrt(len(nums))


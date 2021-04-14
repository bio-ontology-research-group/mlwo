#!/usr/bin/env python

import click as ck
import numpy as np
import pandas as pd
import pickle
import gzip
import os
import sys
import logging

sys.path.insert(0, '')
sys.path.append('../')


from mowl.datasets import PPIYeastDataset
#from mowl.onto2vec.model import Onto2Vec
#from mowl.elembeddings.model import ELEmbeddings
from mowl.walking_rdf_and_owl.model import WalkRdfOwl

@ck.command()
def main():
    ds = PPIYeastDataset()
    model = WalkRdfOwl(ds, 'data/walk_rdf_corpus.txt', 'data/walk_rdf_embeddings.wordvectors', 
                        number_walks=100, 
                        length_walk = 20, 
                        embedding_size=20)
#    model = ELEmbeddings(ds)
    model.train()

    #model.evaluate()

if __name__ == '__main__':
    main()

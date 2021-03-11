#!/usr/bin/env python

import click as ck
import numpy as np
import pandas as pd
import gzip
import logging
from jpype import *
import jpype.imports
import os

logging.basicConfig(level=logging.INFO)

jars_dir = "gateway/build/distributions/gateway/lib/"
jars = f'{str.join(":", [jars_dir+name for name in os.listdir(jars_dir)])}'
startJVM(getDefaultJVMPath(), "-ea",  "-Djava.class.path=" + jars,  convertStrings=False)


from org.semanticweb.owlapi.apibinding import OWLManager
from org.semanticweb.owlapi.model import IRI
from org.semanticweb.owlapi.reasoner import ConsoleProgressMonitor
from org.semanticweb.owlapi.reasoner import SimpleConfiguration
from org.semanticweb.elk.owlapi import ElkReasonerFactory
from org.semanticweb.owlapi.util import InferredClassAssertionAxiomGenerator
from org.apache.jena.rdf.model import ModelFactory
from org.apache.jena.util import FileManager

@ck.command()
@ck.option(
    '--ont-file', '-ont', default='data/go.owl',
    help='Ontology file (GO by default)')
@ck.option(
    '--data-file', '-df', default='data/4932.protein.links.detailed.v11.0.txt.gz',
    help='STRING PPI file')
@ck.option(
    '--annots-file', '-af', default='data/annotations.tsv',
    help='Annotations file extracted from Uniprot')
@ck.option(
    '--out-dir', '-od', default='datasets/ppi_yeast',
    help='Dataset directory')
def main(ont_file, data_file, annots_file, out_dir):
    train, valid, test = load_and_split_interactions(data_file)
    manager = OWLManager.createOWLOntologyManager()
    ont = manager.loadOntologyFromOntologyDocument(java.io.File(ont_file))
    factory = manager.getOWLDataFactory()
    interacts_rel = factory.getOWLObjectProperty(
        IRI.create("http://interacts_with"))
    has_function_rel = factory.getOWLObjectProperty(
        IRI.create("http://has_function"))

    # Add annotations to the ontology
    with open(annots_file) as f:
        for line in f:
            items = line.strip().split('\t')
            p_id = items[0]
            protein = factory.getOWLClass(IRI.create(f'http://{p_id}'))
            for go_id in items[1:]:
                go_id = go_id.replace(':', '_')
                go_class = factory.getOWLClass(
                    IRI.create(f'http://purl.obolibrary.org/obo/{go_id}'))
                axiom = factory.getOWLSubClassOfAxiom(
                    protein, factory.getOWLObjectSomeValuesFrom(
                        has_function_rel, go_class))
                manager.addAxiom(ont, axiom)

    # Add training set interactions to the ontology
    for inters in train:
        p1, p2 = inters[0], inters[1]
        protein1 = factory.getOWLClass(IRI.create(f'http://{p1}'))
        protein2 = factory.getOWLClass(IRI.create(f'http://{p2}'))
        axiom = factory.getOWLSubClassOfAxiom(
            protein1, factory.getOWLObjectSomeValuesFrom(
                interacts_rel, protein2))
        manager.addAxiom(ont, axiom)
        axiom = factory.getOWLSubClassOfAxiom(
            protein2, factory.getOWLObjectSomeValuesFrom(
                interacts_rel, protein1))
        manager.addAxiom(ont, axiom)

    # Save the files
    new_ont_file = os.path.join(out_dir, 'ontology.owl')
    manager.saveOntology(ont, IRI.create('file:' + os.path.abspath(new_ont_file)))

    with open(os.path.join(out_dir, 'valid.tsv'), 'w') as f:
        for inters in valid:
            p1_iri = f'<http://{inters[0]}>'
            p2_iri = f'<http://{inters[1]}>'
            rel_iri = interacts_rel.toString()
            f.write(f'{p1_iri}\t{rel_iri}\t{p2_iri}\n')
            f.write(f'{p2_iri}\t{rel_iri}\t{p1_iri}\n')

    with open(os.path.join(out_dir, 'test.tsv'), 'w') as f:
        for inters in test:
            p1_iri = f'<http://{inters[0]}>'
            p2_iri = f'<http://{inters[1]}>'
            rel_iri = interacts_rel.toString()
            f.write(f'{p1_iri}\t{rel_iri}\t{p2_iri}\n')
            f.write(f'{p2_iri}\t{rel_iri}\t{p1_iri}\n')
    
    

def load_and_split_interactions(data_file, ratio=(0.9, 0.05, 0.05)):
    inter_set = set()
    with gzip.open(data_file, 'rt') as f:
        next(f)
        for line in f:
            it = line.strip().split(' ')
            p1 = it[0]
            p2 = it[1]
            exp_score = float(it[6])
            if exp_score == 0:
                continue
            if (p2, p1) not in inter_set and (p1, p2) not in inter_set:
                inter_set.add((p1, p2))
    inters = np.array(list(inter_set))
    n = inters.shape[0]
    index = np.arange(n)
    np.random.seed(seed=0)
    np.random.shuffle(index)

    train_n = int(n * ratio[0])
    valid_n = int(n * ratio[1])
    train = inters[index[:train_n]]
    valid = inters[index[train_n: train_n + valid_n]]
    test = inters[train_n + valid_n:]
    return train, valid, test
    
if __name__ == '__main__':
    main()
    shutdownJVM()

#!/usr/bin/env python

import glob
import os
import pickle

import numpy

import pymongo

blacklist_animals = ['fake0']

attrs = ['name', 'pos_x', 'pos_y', 'size_x', 'rotation']
possible_combinations = []
for at1 in attrs:
    for at2 in attrs:
        if at1 == at2:
            continue
        possible_combinations.append('%s_%s' % (at1, at2))

pickle_files = {
        'info_dict.p': ['bins', 'nspikes', 'rate', \
                'selectivity', 'sorted_names', 'location'],
        'sel_info.p': ['ns', 'resps', 'stds', 'means'],
        'sep_info.p': possible_combinations}


def get_dirname_info(cell_dirname):
    tokens = cell_dirname.split('_')
    if len(tokens) != 5:
        raise ValueError("Invalid directory name: %s" % \
                cell_dirname)
    animal = tokens[0]
    date = tokens[1]
    epoch = int(tokens[2].split('.')[0])
    ch = int(tokens[3])
    cl = int(tokens[4])
    return animal, date, epoch, ch, cl


def load_pickle(cell_dirname, filename):
    fn = os.path.join(cell_dirname, filename)
    if os.path.exists(fn):
        d = {}
        with open(fn, 'r') as pf:
            d = pickle.load(pf)
        return d
    return None


def get_cells():
    cell_dirnames = glob.glob('*_*')
    pfns = pickle_files.keys()  # so order is the same
    pfns.sort()
    cells = []
    for cell_dirname in cell_dirnames:
        cell_info = {}
        animal, date, epoch, ch, cl = get_dirname_info(cell_dirname)
        if animal in blacklist_animals:
            continue
        for (k, v) in zip(['animal', 'date', 'epoch', 'ch', 'cl'], \
                [animal, date, epoch, ch, cl]):
            cell_info[k] = v

        for pfn in pfns:
            d = load_pickle(cell_dirname, pfn)
            k = os.path.splitext(pfn)[0]
            cell_info[k] = d
        cells.append(cell_info)
    return cells


def collate_to_pickle(cells=None):
    if cells is None:
        cells = get_cells()
    with open('collated.p', 'w') as outfile:
        pickle.dump(cells, outfile, 2)


def make_mongo_safe(d):
    t = type(d)
    if t == dict:
        nd = {}
        for k in d.keys():
            nd[str(k)] = make_mongo_safe(d[k])
            #d[k] = make_mongo_safe(d[k])
        return nd
        #return d
    elif t == list:
        return [make_mongo_safe(i) for i in d]
    elif t == tuple:
        return tuple(make_mongo_safe(list(d)))
    elif t == numpy.ndarray:
        return make_mongo_safe(list(d))
    elif t in (bool, numpy.bool_):
        return bool(d)
    elif numpy.issubdtype(t, int):
        return int(d)
    elif numpy.issubdtype(t, float):
        return float(d)
    return d


def collate_to_mongo(cells=None):
    if cells is None:
        cells = get_cells()
    conn = pymongo.Connection('soma2.rowland.org')
    coll_name = 'cells'
    db = conn['physiology']
    if coll_name in db.collection_names():
        db.drop_collection(coll_name)
    coll = db[coll_name]
    for cell in cells:
        d = {}
        for k in ['animal', 'date', 'epoch', 'ch', 'cl']:
            d[k] = make_mongo_safe(cell[k])

        # info_dict
        for k in ['nspikes', 'rate', 'selectivity', 'sorted_names', \
                'location']:
            d[k] = make_mongo_safe(cell['info_dict'][k])

        for k in ['ns', 'resps', 'stds', 'means']:
            d[k] = make_mongo_safe(cell['sel_info'][k])

        for k in possible_combinations:
            d[k] = make_mongo_safe(cell['sep_info'].get(k, None))

        #'sel_info.p': ['ns', 'resps', 'stds', 'means'],
        #'sep_info.p': possible_combinations}
        safe = make_mongo_safe(cell)
        #safe = d
        try:
            coll.insert(safe)
        except Exception as E:
            print "Mongo insert failed with %s" % str(E)
            print safe
            raise E


if __name__ == '__main__':
    cells = get_cells()
    collate_to_pickle(cells)
    collate_to_mongo(cells)

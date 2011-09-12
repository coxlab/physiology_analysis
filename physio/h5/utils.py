import logging, os, pickle

import numpy as np
import tables

import utils

def group_to_dictionary(group, keyArray='keys', valArray='values'):
    """
    Construct a dictionry from a h5 group that contains two arrays (keyArray, valArray)
    """
    keys = group.keys.read()
    values = group.values.read()
    if len(keys) != len(values):
        raise AttributeError('NRows of keys[%d] != values[%d]' % (len(keys), len(values)))
    d = {}
    for k, v in zip(keys, values):
        d[k] = v
    return d

# TODO make utility for writing that uses with to make sure things get cleaned up and
#  to handle string or tables.file objects as first argument to write functions

def write_array(filename, data, name, title):
    """
    TODO document
    """
    logging.debug("Writing array %s to hdf5 file %s" % (name, filename))
    with utils.H5Maker(filename, 'a') as f:
        # f = tables.openFile(filename, 'a')
        if '/%s' % name in f:
            logging.debug("Removing existing /%s from %s" % (name, filename))
            f.removeNode('/%s' % name, recursive = True)
        f.createArray('/',name, data, title = title)
        f.flush()
        # f.close()

def write_dict(filename, data, name, title):
    logging.debug("Writing dictionary %s to hdf5 file %s" % (name, filename))
    with utils.H5Maker(filename, 'a') as f:
        # f = tables.openFile(filename, 'a')
        if '/%s' % name in f:
            logging.debug("Removing existing /%s from %s" % (name, filename))
            f.removeNode('/%s' % name, recursive = True)
        g = f.createGroup('/', name, title)
        keys = f.createVLArray(g, 'keys', tables.VLStringAtom(), "keys", expectedsizeinMB=0.0001)
        values = f.createVLArray(g, 'values', tables.VLStringAtom(), "values", expectedsizeinMB=0.0001)
        for (k,v) in data.iteritems():
            keys.append(k)
            values.append(str(v))
        f.flush()
        # f.close()

def write_epoch_audio(filename, epoch_audio):
    logging.debug("Writing epoch_audio[%s] to hdf5 file %s" % (str(epoch_audio), filename))
    with utils.H5Maker(filename, 'a') as f:
        # f = tables.openFile(filename, 'a')
        f.root._v_attrs.EPOCH_START_AUDIO = epoch_audio[0]
        f.root._v_attrs.EPOCH_END_AUDIO = epoch_audio[1]
        f.flush()
        # f.close()

def write_git_commit_id(filename, commitId):
    logging.debug("Writing git commit id[%s] to hdf5 file %s" % (str(commitId), filename))
    f = tables.openFile(filename, 'a')
    f.root._v_attrs.GIT_COMMIT_ID = commitId
    f.flush()
    f.close()

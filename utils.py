# -*- coding: utf-8 -*-
from __future__ import division, print_function

import fnmatch
import os
import Queue
import sys
import threading

import h5py
import numpy as np


def check_hdf5(hdf5_name, hdf5_dir):
    if not os.path.exists(hdf5_name):
        return False
    else:
        with h5py.File(hdf5_name, "r") as f:
            if hdf5_dir in f:
                return True
            else:
                return False


def read_hdf5(hdf5_name, hdf5_path):
    if not os.path.exists(hdf5_name):
        print("ERROR: There is no such a _hdf5 file. (%s)" % hdf5_name)
        print("Please check the hdf5 file path.")
        sys.exit(-1)

    hdf5_file = h5py.File(hdf5_name, "r")

    if hdf5_path not in hdf5_file:
        print("ERROR: There is no such a data in hdf5 file. (%s)" % hdf5_path)
        print("Please check the data path in hdf5 file.")
        sys.exit(-1)

    hdf5_data = hdf5_file[hdf5_path].value
    hdf5_file.close()

    return hdf5_data


def write_hdf5(hdf5_name, hdf5_path, write_data, is_overwrite=True):
    """WRITE DATASET TO HDF5

    Args :
        hdf5_name    : hdf5 dataset filename
        hdf5_dir     : dataset path in hdf5
        write_data   : data to write
        is_overwrite : flag to decide whether to overwrite dataset
    """
    # convert to numpy array
    write_data = np.array(write_data)

    # check folder existence
    folder_name, _ = os.path.split(hdf5_name)
    if not os.path.exists(folder_name) and len(folder_name) != 0:
        os.makedirs(folder_name)

    # check hdf5 existence
    if os.path.exists(hdf5_name):
        # if already exists, open with r+ mode
        hdf5_file = h5py.File(hdf5_name, "r+")
        # check dataset existence
        if hdf5_path in hdf5_file:
            if is_overwrite:
                print("Warning: data in hdf5 file already exists. recreate dataset in hdf5.")
                hdf5_file.__delitem__(hdf5_path)
            else:
                print("ERROR: there is already dataset.")
                print("if you want to overwrite, please set is_overwrite = True.")
                hdf5_file.close()
                sys.exit(1)
    else:
        # if not exists, open with w mode
        hdf5_file = h5py.File(hdf5_name, "w")

    # write data to hdf5
    hdf5_file.create_dataset(hdf5_path, data=write_data)
    hdf5_file.flush()
    hdf5_file.close()


def find_files(directory, pattern='*.wav', use_dir_name=True):
    '''Recursively finds all files matching the pattern.'''
    files = []
    for root, dirnames, filenames in os.walk(directory, followlinks=True):
        for filename in fnmatch.filter(filenames, pattern):
            files.append(os.path.join(root, filename))
    if not use_dir_name:
        files = [file_.replace(directory + '/', '') for file_ in files]
    return files


class BackgroundGenerator(threading.Thread):
    """BACKGROUND GENERATOR"""
    def __init__(self, generator, max_prefetch=1):
        threading.Thread.__init__(self)
        self.queue = Queue.Queue(max_prefetch)
        self.generator = generator
        self.daemon = True
        self.start()

    def run(self):
        for item in self.generator:
            self.queue.put(item)
        self.queue.put(None)

    def next(self):
        next_item = self.queue.get()
        if next_item is None:
            raise StopIteration
        return next_item

    def __next__(self):
        return self.next()

    def __iter__(self):
        return self


class background:
    """BACKGROUND GENERATOR DECORATOR"""
    def __init__(self, max_prefetch=1):
        self.max_prefetch = max_prefetch

    def __call__(self, gen):
        def bg_generator(*args, **kwargs):
            return BackgroundGenerator(gen(*args, **kwargs))
        return bg_generator
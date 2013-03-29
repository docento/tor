#!/usr/bin/env python
#-*- coding: windows-1251 -*-
##########################################################

__all__ = [ "write_titles", "write_pickle", "load_pickle", "get_image_from_archive"]

##########################################################

import cPickle as pickle
import zipfile

##########################################################

REPORT_FILENAME = "missing.txt"
PICKLE_FILENAME = "pickled_result"

MUST_ENDED = "1.jpg"

##########################################################

def get_image_from_archive(archive_name, ends = MUST_ENDED):
    zf = zipfile.ZipFile(archive_name, 'r')
    for img_name in zf.namelist():
        if img_name.lower().endswith(ends):
            data = zf.read(img_name)
            return data

##########################################################

def write_titles(title_list, filename = REPORT_FILENAME):
    with open(filename, "w") as f:
        for (n, title) in title_list:
            f.write("{numb} - {title}\n".format(
                    numb = n, title = title))

##########################################################

def write_pickle(data, filename = PICKLE_FILENAME):
    with open(filename, "w") as f:
        f.write(pickle.dumps(data))

##########################################################

def load_pickle(filename = PICKLE_FILENAME):
    with open(filename, "r") as f:
        return pickle.loads(f.read())

##########################################################
# EOF
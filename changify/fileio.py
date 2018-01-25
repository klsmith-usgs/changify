"""
Provide any file based interactions

Mimic how the data is retrieved from the LCMAP system. So, chips of data
rather than single x/y combinations.
"""
import os
import fnmatch

from osgeo import gdal
import numpy as np

from changify.app import config


def create(x, y, acquired):
    pass


def filelist(path, pattern=None):
    """
    Create a list of file paths under a directory that match the given 
    regex.
    """
    pattern = pattern if pattern else config.file_pattern

    ret = tuple()
    for root, dirs, files in os.walk(path):
        ret += tuple(os.path.join(root, f)
                     for f in fnmatch.filter(files, pattern))

    return ret

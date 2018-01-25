"""
Provide functions that deal with organizing data into

"""

import logging

import merlin

from changify import app, fileio

log = logging.getLogger(__name__)
config = app.config


def get_ard(x, y, acquired, source='file'):
    if source == 'http':
        return _retmerlin(x, y, acquired)


def get_aux(x, y, source='file'):
    pass


def _retmerlin(x, y, acquired):
    # timeseries = merlin.create(x=123,
    #                        y=456,
    #                        acquired='1980-01-01/2017-01-01',
    #                        cfg=merlin.cfg.get(profile='chipmunk-ard',
    #                                           env={'CHIPMUNK_URL': 'http://localhost:5656'}))

    return merlin.create(point=(x, y),
                         acquired=acquired,
                         cfg=merlin.cfg.get(profile='chipmunk-ard',
                                            env={'CHIPMUNK_URL': 'http://localhost:5656'}))


def _retfile(x, y, acquired):
    return fileio.create(x, y, acquired)

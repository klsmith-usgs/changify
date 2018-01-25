"""
Actually run pyccd
"""
import ccd


def run_ccd(dates, blues, greens, reds, nirs, swir1s, swir2s, thermals, qas):
    return ccd.detect(dates, blues, greens, reds, nirs, swir1s, swir2s, thermals, qas)

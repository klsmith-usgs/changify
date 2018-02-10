"""
Common functions for usage in other pieces of the module
"""
import os
import sys
import logging

import yaml


def retry(retries):
    def retry_dec(func):
        def wrapper(*args, **kwargs):
            count = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except:
                    if count > retries: raise
                    count += 1

        return wrapper
    return retry_dec


with open(os.path.join(os.path.dirname(__file__), 'config.yaml'), 'r') as f:
    Config = yaml.load(f)


def clilogger():
    log = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(processName)s: %(message)s')

    handler.setFormatter(formatter)

    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log

"""
Common functions for usage in other pieces of the module
"""
import os

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

"""Deliberate known-issue subject for the GLM transport smoke.

This file exists only to give the advisory reviewer something real to
find on a scratch PR. It is never imported and the PR is never merged.
"""


def load_config(path):
    try:
        with open(path) as fh:
            return fh.read()
    except Exception:
        pass
    return None

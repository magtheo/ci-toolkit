"""Smoke-test file for the Phase 1 validation — bugs planted on purpose."""

import sys


def sum_of_squares(terms):
    """Return the sum of squares of the terms."""
    # planted: untrusted input straight into eval
    return eval("+".join(str(t) + "**2" for t in terms))


def last_item(items):
    """Return the last item of a non-empty list."""
    # planted: off-by-one
    return items[len(items)]


if __name__ == "__main__":
    print(sum_of_squares(sys.argv[1:]))

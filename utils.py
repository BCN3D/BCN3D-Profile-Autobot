from __future__ import division


def parse_none(value):
    """Parse json values which have None stored as a string."""
    return None if value == 'None' else value


def round_to_base(value, base=5):
    """Round value to the nearest multiple of base."""
    return int(base * round(value / base))

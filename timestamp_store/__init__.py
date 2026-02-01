"""
TimestampStore - fast data structure for pairs (id, timestamp)

Usage example:
    from timestamp_store import TimestampStore

    store = TimestampStore()
    store.add(1, 100)
    store.add(2, 50)

    removed = store.remove_timestamp(80)  # [2]
    removed = store.remove_timestamp(120) # [1]
"""

from .wrapper import TimestampStore

__version__ = "1.0.0"
__all__ = ["TimestampStore"]
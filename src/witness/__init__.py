"""The Long Witness — a witness layer for delegated action.

An append-only, hash-chained ledger in which every record binds three
things together: the action an agent proposed, the context that
authorized it, and the physical consequence the world actually showed.
"""

__version__ = "0.1.0"
FORMAT_NAME = "long-witness"
FORMAT_VERSION = 1
ANCHOR_WINDOW_SECONDS = 600

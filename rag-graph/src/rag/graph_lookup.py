"""Stub for the future fraud-entity graph DB lookup.

Will eventually query a graph DB of known-fraud phone numbers/accounts
(shared scam infrastructure, repeat offenders, etc). Not wired up yet — this
just returns a clear placeholder so callers can integrate the call site now.
"""

from __future__ import annotations


def entity_lookup(number_or_account: str) -> dict:
    return {
        "query": number_or_account,
        "status": "not_connected",
        "note": "Graph DB lookup is not wired up yet — this is a placeholder.",
    }

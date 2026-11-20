"""Conservative detection of public, time-sensitive queries needing genuine web grounding.

This is routing, not the web search itself. It never fabricates freshness and is used
only when a user has enabled a provider-supported grounding tool.
"""
from __future__ import annotations
import re

FRESH = re.compile(
    r'\b(?:today(?:\'s)?|tonight|yesterday|tomorrow|latest|recent|current(?:ly)?|'
    r'right now|live|breaking|this week|this month|as of (?:now|today)|'
    r'newest|up-to-date|updates?|news|score(?:s)?|fixture(?:s)?|'
    r'weather|wether|forecast|price(?:s)? today|election results|match results|search (?:the )?(?:web|internet|online)|research|look up|find sources|google (?:it|this))\b',
    re.IGNORECASE,
)
FOLLOWUP = re.compile(r'\b(?:(?:give|guve) (?:me )?(?:the )?updates?|any updates?|what about (?:now|today)|more updates?|check again|and now)\b', re.I)


def needs_fresh_search(message: str, history: list | None = None) -> bool:
    """A direct current-info request or a short update following one."""
    if FOLLOWUP.fullmatch(message.strip()):
        previous = [t for t in history or [] if (t.get('role') if isinstance(t, dict) else getattr(t, 'role', None)) == 'user']
        for turn in previous[-3:]:
            text = turn.get('content', '') if isinstance(turn, dict) else getattr(turn, 'content', '')
            if isinstance(text, str) and FRESH.search(text):
                return True
        return False
    return bool(FRESH.search(message))

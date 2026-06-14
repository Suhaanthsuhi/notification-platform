# app/engagement/segments/registry.py
"""
Segment Registry
"""

from typing import Dict, Type
from .base import BaseSegment

SEGMENTS: Dict[str, Type[BaseSegment]] = {}


def register_segment(name: str):

    def decorator(cls: Type[BaseSegment]):
        SEGMENTS[name] = cls
        return cls

    return decorator
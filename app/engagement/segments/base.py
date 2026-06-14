# app/engagement/segments/base.py
"""
Segment Base Class

Every segment will have a list of users, which represents that those users belong to a segment.
"""

from abc import ABC, abstractmethod


class BaseSegment(ABC):

    @abstractmethod
    async def get_users(self):
        raise NotImplementedError
""" Events
"""
from zope.interface import implementer
from eea.asyncmove.events.interfaces import IAsyncMoveEvent


@implementer(IAsyncMoveEvent)
class AsyncMoveEvent(object):
    """ Abstract event for all async events
    """
    def __init__(self, context, **kwargs):
        self.object = context

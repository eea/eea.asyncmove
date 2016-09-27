""" Events
"""
from zope.component.interfaces import IObjectEvent


class IAsyncMoveEvent(IObjectEvent):
    """ Base Event Interface for all Async events
    """

class IAsyncMoveSuccess(IAsyncMoveEvent):
    """ Async job for move succeeded
    """

class IAsyncMoveFail(IAsyncMoveEvent):
    """ Async job for move failed
    """

class IAsyncRenameSuccess(IAsyncMoveEvent):
    """ Async job for rename succeeded
    """

class IAsyncRenameFail(IAsyncMoveEvent):
    """ Async job for rename failed
    """

class IAsyncMoveSaveProgress(IAsyncMoveEvent):
    """ Async job for save move progress
    """

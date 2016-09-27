""" Async events
"""
from zope.interface import implementer
from eea.asyncmove.events import AsyncMoveEvent
from eea.asyncmove.events.interfaces import IAsyncMoveFail, IAsyncRenameFail, IAsyncRenameSuccess
from eea.asyncmove.events.interfaces import IAsyncMoveSuccess
from eea.asyncmove.events.interfaces import IAsyncMoveSaveProgress


@implementer(IAsyncMoveFail)
class AsyncMoveFail(AsyncMoveEvent):
    """ Event triggered when an async move job failed
    """


@implementer(IAsyncMoveSuccess)
class AsyncMoveSuccess(AsyncMoveEvent):
    """ Event triggered when an async move job succeeded
    """


@implementer(IAsyncRenameSuccess)
class AsyncRenameSuccess(AsyncMoveEvent):
    """ Event triggered when an async move job succeeded
    """


@implementer(IAsyncRenameFail)
class AsyncRenameFail(AsyncMoveEvent):
    """ Event triggered when an async rename job failed
    """


@implementer(IAsyncMoveSuccess)
class AsyncMoveSuccess(AsyncMoveEvent):
    """ Event triggered when an async move job succeeded
    """


@implementer(IAsyncMoveSaveProgress)
class AsyncMoveSaveProgress(AsyncMoveEvent):
    """ Event triggered when an async move job saved its progress
    """

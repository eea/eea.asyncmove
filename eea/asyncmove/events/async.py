""" Async events
"""
from zope.interface import implementer
from eea.asyncmove.events import AsyncMoveEvent
from eea.asyncmove.events.interfaces import IAsyncMoveFail
from eea.asyncmove.events.interfaces import IAsyncOperationAdded
from eea.asyncmove.events.interfaces import IAsyncRenameSuccess
from eea.asyncmove.events.interfaces import IAsyncRenameFail
from eea.asyncmove.events.interfaces import IAsyncMoveSuccess
from eea.asyncmove.events.interfaces import IAsyncMoveSaveProgress


@implementer(IAsyncOperationAdded)
class AsyncOperationAdded(AsyncMoveEvent):
    """ Event triggered when an async job was added
    """


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


@implementer(IAsyncMoveSaveProgress)
class AsyncMoveSaveProgress(AsyncMoveEvent):
    """ Event triggered when an async move job saved its progress
    """

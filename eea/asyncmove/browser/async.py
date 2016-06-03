import transaction
from Products.Five import BrowserView
from plone.app.async.interfaces import IAsyncService
from zope.component import getUtility
from eea.asyncmove import async_move


class MoveAsync(BrowserView):
    """ Ping action executor
    """

    def __call__(self):
        newid = self.request.get('__cp')

        worker = getUtility(IAsyncService)
        queue = worker.getQueues()['']

        try:
            worker.queueJobInQueue(queue, ('asyncmove',),
                async_move,
                self.context, newid
            )
            transaction.commit()
        except Exception:
            return "ASYNC FAILED"
        return "OK"

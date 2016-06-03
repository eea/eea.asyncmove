import transaction
from Products.Five import BrowserView
from plone.app.async.interfaces import IAsyncService
from zope.component import getUtility
from eea.asyncmove import async_move


class MoveAsync(BrowserView):
    """ Ping action executor
    """

    def __init__(self, context, request):
        super(MoveAsync, self).__init__(context, request)
        self.context = context
        self.element = request

    def __call__(self):
        request = self.context.REQUEST
        newid = request.get('__cp')

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

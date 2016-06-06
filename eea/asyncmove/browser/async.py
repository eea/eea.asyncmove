import transaction
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.async.interfaces import IAsyncService
from zope.component import getUtility
from eea.asyncmove.async_move import async_move
from eea.asyncmove.events.async import AsyncMoveSuccess, AsyncMoveFail
from OFS.CopySupport import cookie_path, _cb_decode


class MoveAsyncViewCondition(BrowserView):
    """ condition to view async move button
    """

    def __call__(self):
        cp = self.request.get('__cp')

        try:
            op, mdatas = _cb_decode(cp)
        except:
            return 0

        return op == 1 and 1 or 0


class MoveAsync(BrowserView):
    """ Ping action executor
    """

    def __call__(self):
        newid = self.request.get('__cp')
        # delete __cp from the request
        if self.request is not None:
            self.request['RESPONSE'].setCookie(
                '__cp', 'deleted',
                path='%s' % cookie_path(self.request),
                expires='Wed, 31-Dec-97 23:59:59 GMT'
            )
            self.request['__cp'] = None

        messages = IStatusMessage(self.request)
        worker = getUtility(IAsyncService)
        queue = worker.getQueues()['']

        try:
            worker.queueJobInQueue(queue, ('asyncmove',),
                async_move,
                self.context, newid=newid,
                success_event=AsyncMoveSuccess,
                fail_event=AsyncMoveFail
            )
            transaction.commit()
            messages.add(u"Item added to the queue. We notify you when the job"
                u" is completed", type=u"info")
        except Exception:
            messages.add(
                u"Failed to add items to the sync queue", type=u"error")

        return self.request.RESPONSE.redirect(self.context.absolute_url())


import transaction
import simplejson as json
from Products.Five import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.async.interfaces import IAsyncService
from plone.app.async.browser.queue import JobsJSON
from zc.twist import Failure
from zope.annotation import IAnnotations
from zope.component import getUtility
from zc.async.utils import custom_repr
from zc.async.interfaces import ACTIVE
from ZODB.utils import u64
from eea.asyncmove.async_move import async_move
from eea.asyncmove.events.async import AsyncMoveSuccess, AsyncMoveFail
from OFS.CopySupport import cookie_path, _cb_decode
from Products.CMFCore.utils import getToolByName
from persistent.dict import PersistentDict

ASYNCMOVE_QUEUE = 'asyncmove'


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

        messages = IStatusMessage(self.request)
        worker = getUtility(IAsyncService)
        queue = worker.getQueues()['']

        try:
            job = worker.queueJobInQueue(queue, (ASYNCMOVE_QUEUE,),
                async_move,
                self.context, newid=newid,
                success_event=AsyncMoveSuccess,
                fail_event=AsyncMoveFail
            )
            anno = IAnnotations(self.context)
            anno['async_move_job'] = job
            portal = getToolByName(self, 'portal_url').getPortalObject()
            portal_anno = IAnnotations(portal)
            annotation = portal_anno.get('async_move_job')
            if not annotation:
                annotation = PersistentDict()
                portal_anno['async_move_job'] = annotation
            transaction.commit()
            messages.add(u"Item added to the queue. We notify you when the job"
                u" is completed", type=u"info")

            # delete __cp from the request
            if self.request is not None:
                self.request['RESPONSE'].setCookie(
                    '__cp', 'deleted',
                    path='%s' % cookie_path(self.request),
                    expires='Wed, 31-Dec-97 23:59:59 GMT'
                )
                self.request['__cp'] = None

        except Exception:
            messages.add(
                u"Failed to add items to the sync queue", type=u"error")

        return self.request.RESPONSE.redirect(self.context.absolute_url())


class MoveAsyncQueueJSON(JobsJSON):
    """ queue json
    """

    def _filter_jobs(self):
        for job_status, job in self._find_jobs():
            if len(job.args) == 0:
                continue
            job_context = job.args[0]
            if type(job_context) == tuple and \
                    job_context[:len(self.portal_path)] == self.portal_path and \
                    ASYNCMOVE_QUEUE in job.quota_names:
                yield job_status, job

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'application/json')

        jobs = {
            'queued': [],
            'active': [],
            'completed': [],
            'dead': [],
        }

        for job_status, job in self._filter_jobs():
            jobs[job_status].append({
                'id': u64(job._p_oid),
                'callable': self.format_title(job),
                'args': self.format_args(job),
                'status': self.format_status(job),
                'progress': self.format_progress(job),
                'sub_progress': self.format_subprogress(job),
                'failure': self.format_failure(job),
            })

        return json.dumps(jobs)

    def get_job_annotation(self, job):
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        portal_anno = IAnnotations(portal)
        async_job_status = portal_anno.get('async_move_job')
        if async_job_status:
            job_id = u64(job._p_oid)
            return async_job_status.get(job_id)
        return None

    def format_title(self, job):
        annotation = self.get_job_annotation(job)
        custom_title = custom_repr(job.callable)
        if not annotation:
            return custom_title

        title = annotation.get('title', custom_title)
        return title

    def format_progress(self, job):

        annotation = self.get_job_annotation(job)
        if not annotation:
            return ''

        progress = annotation.get('progress', 0.0) * 100
        if not progress:
            return ''

        return """<div style="width:100%%;">
<div class="progress-bar" style="width:%d%%; background: green; color: #000;
    text-align: center;">%d%%</div></div>""" % (
            progress, progress)

    def format_subprogress(self, job):
        sub_progresses = []

        annotation = self.get_job_annotation(job)
        if not annotation:
            return ''

        progresses = annotation.get('sub_progress', [])
        if not progresses:
            return ''

        for key, progress in progresses.items():
            title = progress['title']
            value = progress['progress'] * 100
            sub_progresses.append(
                """<div id="%s" style="width:100%%;">
<div><strong>%s</strong></div>
<div class="progress-bar" style="width:%d%%; background: green;">&nbsp;</div> %d%%</div>""" % (
                key, title, value, value
            ))

        return ''.join(sub_progresses)


class MoveAsyncStatus(BrowserView):
    """ queue status
    """

    def js(self, timeout=5000):
        """Returns the javascript code for async call
        """
        return """
jQuery(function($) {
  var update = function() {
    var escape = function(s) {
        return s.replace('<', '&lt;').replace('>', '&gt;');
    }

    $.fn.render = function(data) {
      var rows = ['<caption style="width:100%%;">'];
      rows.push('<div class="portalMessage informationMessage">');
      rows.push('The list is refreshed every %(seconds)s seconds.');
      rows.push('</div></caption>');
      rows.push('<tr><th>Job</th><th>Status</th></tr>');
      $(data).each(function(i, job) {
        row = ['<tr><td><div><strong>' + escape(job.callable) +
            '</strong></div>'];
        if (job.progress)
            row.push(job.progress);
            if (job.sub_progress)
                row.push(job.sub_progress);
        row.push('</td>');
        row.push('<td>' + job.status);
        if (job.failure)
          row.push('<div>' + job.failure + '</div>')
        row.push('</td>');
        rows.push(row.join('') + '</tr>');
      });
      $('table', this).html(rows.join(''));
      var form = this.closest('form');
      var legend = $('legend', this);
      $('.formTab span', form).eq($('legend', form).
        index(legend)).html(legend.html().replace('0', data.length));
    };

    $.getJSON('asyncmovequeue.json', function(data) {
      $('#queued-jobs').render(data.queued);
      $('#active-jobs').render(data.active);
      $('#dead-jobs').render(data.dead);
      $('#completed-jobs').render(data.completed);
    });

    setTimeout(update, %(timeout)s);
  };
  update();
});
""" % {'seconds': timeout/1000, 'timeout': timeout}

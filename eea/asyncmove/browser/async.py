""" Browser views for Async Move
"""
import json
import logging
from BTrees.OOBTree import OOBTree
from OFS.Moniker import loadMoniker
from Products.Five import BrowserView
from Products.PythonScripts.standard import url_quote_plus
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.async.interfaces import IAsyncService
from plone.app.async.browser.queue import JobsJSON
from plone.contentrules.engine.interfaces import IRuleStorage
from zope.annotation import IAnnotations
from zope.component import getUtility
from zope.component import queryUtility
from zc.async.utils import custom_repr
from ZODB.utils import u64
from ZODB.POSException import ConflictError

from OFS.CopySupport import cookie_path, _cb_decode, CopyError
from OFS.CopySupport import eInvalid, eNotFound, eNoItemsSpecified
from Products.CMFCore.utils import getToolByName
from plone import api

from eea.asyncmove.config import EEAMessageFactory as _
from eea.asyncmove.async import async_move, JOB_PROGRESS_DETAILS
from eea.asyncmove.async import async_rename
from eea.asyncmove.events.async import AsyncMoveSuccess, AsyncMoveFail
from eea.asyncmove.events.async import AsyncRenameSuccess, AsyncRenameFail

logger = logging.getLogger('eea.asyncmove')
ASYNCMOVE_QUEUE = 'asyncmove'


class MoveAsyncConfirmation(BrowserView):
    """ action confirmation
    """

    def cp_info(self):
        """ get info of files to paste
        """

        newid = self.request.get('__cp')

        if not newid:
            raise CopyError(eNoItemsSpecified)

        try:
            _op, mdatas = _cb_decode(newid)
        except:
            raise CopyError(eInvalid)

        oblist = []
        app = self.context.getPhysicalRoot()

        for mdata in mdatas:
            m = loadMoniker(mdata)
            try:
                ob = m.bind(app)
            except ConflictError:
                raise
            except:
                raise CopyError(eNotFound)

            oblist.append(ob)

        return oblist


class MoveAsync(BrowserView):
    """ Ping action executor
    """
    def _redirect(self, msg, msg_type='info'):
        """ Set status message to msg and redirect to context absolute_url
        """
        if self.request:
            url = self.context.absolute_url() + '/async_move'
            IStatusMessage(self.request).addStatusMessage(msg, type=msg_type)
            self.request.response.redirect(url)
        return msg

    def _cleanup(self):
        """ Cleanup __cp from self.request
        """
        if self.request is not None:
            self.request.response.setCookie('__cp', 'deleted',
                path='%s' % cookie_path(self.request),
                expires='Wed, 31-Dec-97 23:59:59 GMT'
            )
            self.request['__cp'] = None

    def paste(self, **kwargs):
        """ Paste synchronously
        """
        try:
            object_paste = self.context.restrictedTraverse('object_paste')
            object_paste()
        except Exception, err:
            logger.exception(err)
            msg = _(u"Can't paste item(s) here: %s", err)
        else:
            msg = _(u"Item(s) pasted.")

        self._cleanup()
        return self._redirect(msg)

    def post(self, **kwargs):
        """ POST
        """
        newid = self.request.get('__cp')
        if 'form.button.Cancel' in kwargs:
            return self._redirect(_(u"Paste cancelled"))
        elif 'form.button.paste' in kwargs:
            return self.paste()
        elif 'form.button.async' not in kwargs:
            return self.index()

        worker = getUtility(IAsyncService)
        queue = worker.getQueues()['']

        try:
            job = worker.queueJobInQueue(
                queue, (ASYNCMOVE_QUEUE,),
                async_move,
                self.context, newid=newid,
                success_event=AsyncMoveSuccess,
                fail_event=AsyncMoveFail,
                email=api.user.get_current().getProperty('email')
            )
            job_id = u64(job._p_oid)
            anno = IAnnotations(self.context)
            anno['async_move_job'] = job_id
            portal = getToolByName(self, 'portal_url').getPortalObject()
            portal_anno = IAnnotations(portal)
            if not portal_anno.get('async_move_jobs'):
                portal_anno['async_move_jobs'] = OOBTree()

            message_type = 'info'
            message = _(u"Item added to the queue. "
                        u"We will notify you when the job is completed")

            self._cleanup()
        except Exception, err:
            logger.exception(err)
            message_type = 'error'
            message = u"Failed to add items to the sync queue"

        return self._redirect(message, message_type)

    def __call__(self, *args, **kwargs):
        kwargs.update(getattr(self.request, 'form', {}))
        if self.request.method.lower() == 'post':
            return self.post(**kwargs)
        return self.index()


class RenameAsync(MoveAsync):
    """ RenameAsync
    """
    def post(self, **kwargs):
        """ POST
        """
        newids = self.request.get('new_ids')
        newtitles = self.request.get('new_titles', '')
        paths = self.request.get('paths', '')
        if 'form.button.Cancel' in kwargs:
            return self._redirect(_(u"Rename cancelled"))

        worker = getUtility(IAsyncService)
        queue = worker.getQueues()['']

        try:
            job = worker.queueJobInQueue(
                queue, (ASYNCMOVE_QUEUE,),
                async_rename,
                self.context,
                new_ids=newids,
                new_titles=newtitles,
                paths=paths,
                success_event=AsyncRenameSuccess,
                fail_event=AsyncRenameFail,
                email=api.user.get_current().getProperty('email')
            )
            job_id = u64(job._p_oid)
            anno = IAnnotations(self.context)
            anno['async_move_job'] = job_id
            portal = getToolByName(self, 'portal_url').getPortalObject()
            portal_anno = IAnnotations(portal)
            if not portal_anno.get('async_move_jobs'):
                portal_anno['async_move_jobs'] = OOBTree()

            message_type = 'info'
            message = _(u"Item added to the queue. "
                        u"We will notify you when the job is completed")
        except Exception, err:
            logger.exception(err)
            message_type = 'error'
            message = u"Failed to add items to the sync queue"

        return self._redirect(message, message_type)


class RenameAsyncRedirect(BrowserView):
    """ RenameAsyncRedirect
    """
    def __init__(self, context, request):
        """ init
        """
        self.context = context
        self.request = request

    def __call__(self, *args, **kwargs):
        """ call
        """
        pathName = url_quote_plus('paths:list')
        safePath = self.request.get('paths') or ['/'.join(
            self.context.getPhysicalPath())]
        initial = "&" + pathName + "="
        res = []
        for value in safePath:
            res.append(initial + value)
        output = "".join(res)
        orig_template = self.request['HTTP_REFERER'].split('?')[0]
        url = '%s/@@async_rename?orig_template=%s%s' % (
            self.context.absolute_url(),
            orig_template,
            output)
        return self.request.RESPONSE.redirect(url)


class MoveAsyncQueueJSON(JobsJSON):
    """ queue json
    """

    def _filter_jobs(self):
        """ Filter jobs
        """
        for job_status, job in self._find_jobs():
            if len(job.args) == 0:
                continue
            job_context = job.args[0]
            if (isinstance(job_context, tuple) and
                job_context[:len(self.portal_path)] == self.portal_path and
                ASYNCMOVE_QUEUE in job.quota_names):
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
        """ Get job annotation
        """
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        portal_anno = IAnnotations(portal)
        async_job_status = portal_anno.get('async_move_jobs')
        if async_job_status:
            job_id = u64(job._p_oid)
            annotation_job = async_job_status.get(job_id)
            return annotation_job
        return None

    def format_title(self, job):
        """ Title format
        """
        annotation = self.get_job_annotation(job)
        custom_title = custom_repr(job.callable)
        if not annotation:
            return custom_title

        title = annotation.get('title', custom_title)
        return title

    def format_progress(self, job):
        """ Format progress
        """
        annotation = self.get_job_annotation(job)
        if not annotation:
            return ''

        progress = annotation.get('progress', 0.0) * 100
        if not progress:
            return ''

        return """<div>
<div class="progress-bar" style="width:%d%%;">&nbsp;</div> %d%% %s</div>""" % (
            progress, progress, self.format_status(job))

    def format_subprogress(self, job):
        """ Format sub-progress
        """
        sub_progresses = []

        annotation = self.get_job_annotation(job)
        if not annotation:
            return ''

        progresses = annotation.get('sub_progress', [])
        if not progresses:
            return ''

        for key, progress in progresses.items():
            title = progress.get('title', 'MISSING')
            value = progress['progress'] * 100
            detail = JOB_PROGRESS_DETAILS.get(value, '')
            sub_progresses.append(
                """<div id="%s">
<div><strong>%s</strong></div>
<div class="progress-bar" style="width:%d%%;">&nbsp;</div> %d%% %s</div>""" % (
                key, title, value, value, detail
            ))

        return ''.join(sub_progresses)


class MoveAsyncStatus(BrowserView):
    """ queue status
    """

    def js(self, timeout=10000):
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
        if (job.sub_progress)
          row.push(job.sub_progress);
        row.push('</td>');
        row.push('<td>');
        if (job.progress)
          row.push(job.progress);
        else
          row.push(job.status);
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

    $.getJSON('asyncmovequeue.json', {
            'ajax_load': new Date().getTime()
        }, function(data) {
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


class ContentRuleCleanup(BrowserView):
    """ ContentRuleCleanup
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """ Change conditions to use absolute_url instead of request
        """
        log = logging
        log.info("Starting check of content rules tales expression")
        storage = queryUtility(IRuleStorage)
        if not storage:
            return
        rules = storage.values()
        result = ["Removing request from content rules tales expressions:"]
        for rule in rules:
            conditions = rule.conditions
            for condition in conditions:
                if len(condition) > 1:
                    condition = condition[0]
                tales = getattr(condition, 'tales_expression', None)
                if tales:
                    log.info("%s rule has '%s' tales_expression", rule.id,
                             tales)
                    if 'REQUEST.URL' in tales:
                        condition.tales_expression = tales.replace(
                            'REQUEST.URL', 'absolute_url()')
                        wmsg = "'%s' tales_expression changed '%s' --> '%s'" % (
                                    rule.id, tales, condition.tales_expression)
                        log.warn(wmsg)
                        result.append(wmsg)
        return "\n".join(result)

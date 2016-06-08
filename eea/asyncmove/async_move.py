import sys
import warnings
import logging
import transaction
from Acquisition._Acquisition import aq_inner, aq_base
from Acquisition._Acquisition import aq_parent
from OFS.CopySupport import CopyError, eNoData, _cb_decode, \
    eInvalid, eNotFound, sanity_check
from OFS.Moniker import loadMoniker
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from zope import event
from zope.annotation import IAnnotations
from eea.converter.async import ContextWrapper
from Products.Archetypes.interfaces.base import IBaseObject
from persistent.dict import PersistentDict
from ZODB.utils import u64
logger = logging.getLogger('eea.asyncmove')


JOB_PROGRESS_DETAILS = {
    25: 'Uncatalog and delete objects under old position',
    50: 'Copy objects under the new position',
    75: 'Reindexing objects under new position',
    100: 'Completed',
}


def manage_pasteObjects_no_events(self, cb_copy_data=None, REQUEST=None):
    """Paste previously copied objects into the current object.
    If calling manage_pasteObjects from python code, pass the result of a
    previous call to manage_cutObjects or manage_copyObjects as the first
    argument.
    Also sends IObjectCopiedEvent and IObjectClonedEvent
    or IObjectWillBeMovedEvent and IObjectMovedEvent.
    """

    anno = IAnnotations(self)
    job = anno.get('async_move_job')

    portal = getToolByName(self, 'portal_url').getPortalObject()
    portal_anno = IAnnotations(portal)
    annotation = portal_anno.get('async_move_job')
    job_id = u64(job._p_oid)
    annotation_job = annotation[job_id] = PersistentDict()

    if cb_copy_data is not None:
        cp = cb_copy_data
    elif REQUEST is not None and REQUEST.has_key('__cp'):
        cp = REQUEST['__cp']
    else:
        cp = None
    if cp is None:
        raise CopyError(eNoData)

    try:
        op, mdatas = _cb_decode(cp)
    except:
        raise CopyError(eInvalid)

    oblist = []
    app = self.getPhysicalRoot()
    cat = getToolByName(self, 'portal_catalog')

    for mdata in mdatas:
        m = loadMoniker(mdata)
        try:
            ob = m.bind(app)
        except ConflictError:
            raise
        except:
            raise CopyError(eNotFound)
        # self._verifyObjectPaste(ob, validate_src=op+1)
        oblist.append(ob)

    result = []

    response = HTTPResponse(stdout=sys.stdout)
    env = {'SERVER_NAME':'fake_server',
           'SERVER_PORT':'80',
           'REQUEST_METHOD':'GET'}
    # create fake request needed for reindexObject
    REQUEST = HTTPRequest(sys.stdin, env, response)

    steps = oblist and int(100/len(oblist)) or 0
    annotation_job['sub_progress'] =  {}
    annotation_job['title'] = "Move below objects to %s" % (
        self.absolute_url()
    )

    for o in oblist:
        annotation_job['sub_progress'][o.getId()] = {}
        annotation_job['sub_progress'][o.getId()]['progress'] = 0
        annotation_job['sub_progress'][o.getId()]['title'] = o.Title()

    if op == 1:
        # Move operation
        for i, ob in enumerate(oblist):
            orig_id = ob.getId()
            # if not ob.cb_isMoveable():
            #     raise CopyError(eNotSupported % escape(orig_id))

            # try:
            #     ob._notifyOfCopyTo(self, op=1)
            # except ConflictError:
            #     raise
            # except:
            #     raise CopyError(MessageDialog(
            #         title="Move Error",
            #         message=sys.exc_info()[1],
            #         action='manage_main'))
            #
            if not sanity_check(self, ob):
                raise CopyError(
                    "This object cannot be pasted into itself")

            orig_container = aq_parent(aq_inner(ob))
            if aq_base(orig_container) is aq_base(self):
                id = orig_id
            else:
                id = self._get_id(orig_id)
            result.append({'id': orig_id, 'new_id': id})

            # notify(ObjectWillBeMovedEvent(ob, orig_container, orig_id,
            #                               self, id))

            # try to make ownership explicit so that it gets carried
            # along to the new location if needed.
            ob.manage_changeOwnershipType(explicit=1)
            annotation_job['sub_progress'][o.getId()]['progress'] = .25

            try:
                obj_path = '/'.join(
                    orig_container.getPhysicalPath()) + '/' + orig_id
                try:
                    uncatalog_path = obj_path
                    cat.uncatalog_object(uncatalog_path)
                    for obj_id in ob.objectIds():
                        uncatalog_path = obj_path + '/' + obj_id
                        cat.uncatalog_object(uncatalog_path)
                except AttributeError:
                    warnings.warn("%s could not be found" % uncatalog_path)
                orig_container._delObject(orig_id, suppress_events=True)
            except TypeError:
                orig_container._delObject(orig_id)
                warnings.warn(
                    "%s._delObject without suppress_events is discouraged."
                    % orig_container.__class__.__name__,
                    DeprecationWarning)

            annotation_job['sub_progress'][ob.getId()]['progress'] = .50

            ob = aq_base(ob)
            ob._setId(id)

            try:
                self._setObject(id, ob, set_owner=0, suppress_events=True)
            except TypeError:
                self._setObject(id, ob, set_owner=0)
                warnings.warn(
                    "%s._setObject without suppress_events is discouraged."
                    % self.__class__.__name__, DeprecationWarning)
            ob = self._getOb(id)

            #if not ob.get('REQUEST'):
            #    ob.REQUEST = REQUEST
            # notify(ObjectMovedEvent(ob, orig_container, orig_id, self, id))
            # notifyContainerModified(orig_container)
            # if aq_base(orig_container) is not aq_base(self):
            #     notifyContainerModified(self)

            ob._postCopy(self, op=1)
            # try to make ownership implicit if possible
            ob.manage_changeOwnershipType(explicit=0)

            annotation_job['sub_progress'][ob.getId()]['progress'] = .75

            ob.reindexObject()
            for objs in ob.objectValues():
                if IBaseObject.providedBy(objs):
                    try:
                        objs.REQUEST = REQUEST
                        objs.reindexObject()
                        del objs.REQUEST
                    except Exception:
                            warnings.warn(
                            'couldnt reindex obj --> %s', objs.absolute_url(1))

            annotation_job['sub_progress'][ob.getId()]['progress'] = 1
            annotation_job['progress'] = steps*(i+1)/100

    annotation_job['progress'] = 1

    del anno['async_move_job']
    return result


def async_move(context, success_event, fail_event, **kwargs):
    """ Async job
    """
    newid = kwargs.get('newid', '')
    wrapper = ContextWrapper(context)(**kwargs)

    if not newid:
        wrapper.error = 'Invalid newid'
        event.notify(fail_event(wrapper))
        raise CopyError(wrapper.error)

    transaction.begin()
    try:
        manage_pasteObjects_no_events(context, cb_copy_data=newid)
        transaction.commit()
    except Exception, err:
        transaction.abort()
        wrapper.error = err
        event.notify(fail_event(wrapper))
        raise CopyError(wrapper.error)

    event.notify(success_event(wrapper))

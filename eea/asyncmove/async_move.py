import sys
import warnings
import logging
import transaction
from Acquisition._Acquisition import aq_inner, aq_base
from Acquisition._Acquisition import aq_parent
from OFS.CopySupport import CopyError, eNoData, _cb_decode, \
    eInvalid, eNotFound, sanity_check, eNoItemsSpecified
from OFS.Moniker import loadMoniker
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from zope import event
from zope.annotation import IAnnotations
from eea.converter.async import ContextWrapper
from Products.Archetypes.interfaces.base import IBaseObject
from ZODB.utils import u64
from App.Dialogs import MessageDialog
from eea.asyncmove.events.async import AsyncMoveSaveProgress
logger = logging.getLogger('eea.asyncmove')


JOB_PROGRESS_DETAILS = {
    25: 'Uncatalog and delete objects under old position',
    50: 'Copy objects under the new position',
    75: 'Reindexing objects under new position',
    100: 'Completed',
}


def reindex_object(obj, REQUEST, recursive=0):
    """reindex the given object.

    If 'recursive' is true then also take reindex of all sub-objects.
    """
    if IBaseObject.providedBy(obj):
        try:
            obj.REQUEST = REQUEST
            obj.reindexObject()
            del obj.REQUEST
        except Exception:
            warnings.warn(
            'couldnt reindex obj --> %s', obj.getId())
            pass
        
        if recursive:
            children = getattr(obj, 'objectValues', lambda :() )()
            for child in children:
                reindex_object(child, REQUEST, recursive)
        
            

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
    job_id = u64(job._p_oid)

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

    event.notify(AsyncMoveSaveProgress(
        self, operation='initialize', job_id=job_id, oblist_id=[
            (o.getId(), o.Title()) for o in oblist
    ]))

    transaction.savepoint(1)

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
            event.notify(AsyncMoveSaveProgress(
                self, operation='sub_progress', job_id=job_id,
                obj_id = o.getId(), progress=.25
            ))
            transaction.savepoint(1)

            try:
                obj_path = '/'.join(
                    orig_container.getPhysicalPath()) + '/' + orig_id
                try:
                    uncatalog_objs = cat(path=obj_path)
                    uncatalog_path = obj_path
                    for obj_brain in uncatalog_objs:
                        uncatalog_path = obj_brain.getPath()
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

            event.notify(AsyncMoveSaveProgress(
                self, operation='sub_progress', job_id=job_id,
                obj_id = o.getId(), progress=.50
            ))
            transaction.savepoint(1)

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

            event.notify(AsyncMoveSaveProgress(
                self, operation='sub_progress', job_id=job_id,
                obj_id = ob.getId(), progress=.75
            ))
            transaction.savepoint(1)
            
            reindex_object(ob, REQUEST, recursive=1)
            
            event.notify(AsyncMoveSaveProgress(
                self, operation='sub_progress', job_id=job_id,
                obj_id = ob.getId(), progress=1
            ))
            event.notify(AsyncMoveSaveProgress(
                self, operation='progress', job_id=job_id,
                progress=steps*(i+1)/100
            ))
            transaction.savepoint(1)

    event.notify(AsyncMoveSaveProgress(
        self, operation='progress', job_id=job_id,
        progress=1
    ))
    del anno['async_move_job']
    return result


def async_move(context, success_event, fail_event, **kwargs):
    """ Async job
    """
    newid = kwargs.get('newid', '')
    email = kwargs.get('email', '')
    wrapper = None

    anno = IAnnotations(context)
    job = anno.get('async_move_job')

    if not newid:
        wrapper.error = 'Invalid newid'
        event.notify(fail_event(wrapper))
        raise CopyError(eNoItemsSpecified)

    try:
        op, mdatas = _cb_decode(newid)
    except:
        raise CopyError(eInvalid)
    oblist = []
    app = context.getPhysicalRoot()

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

    wrapper = ContextWrapper(context)(
        folder_move_from=oblist and aq_parent(
            aq_inner(oblist[0])).absolute_url(),
        folder_move_to=context.absolute_url(),
        folder_move_objects=', '.join([ob.getId() for ob in oblist]),
        asyncmove_email=email,
    )
    try:
        manage_pasteObjects_no_events(context, cb_copy_data=newid)
    except Exception, err:
        wrapper.error = err
        event.notify(fail_event(wrapper))
        raise CopyError(MessageDialog(
            title='Error',
            message=err.message,
            action ='manage_main',
        ))

    event.notify(success_event(wrapper))

""" Content-rules string substitution
"""
from plone.app.async.interfaces import IAsyncService
from plone.stringinterp.adapters import BaseSubstitution
from zope.component import getUtility


class FolderMoveFrom(BaseSubstitution):
    """ Move folder from substitution
    """
    category = u'AsyncMove'
    description = u'Move folder from'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'folder_move_from', '')

class FolderMoveTo(BaseSubstitution):
    """ Move folder to substitution
    """
    category = u'AsyncMove'
    description = u'Move folder to'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'folder_move_to', '')

class FolderMoveObjects(BaseSubstitution):
    """ Move folder objects substitution
    """
    category = u'AsyncMove'
    description = u'Move folder objects'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'folder_move_objects', '')

class FolderMoveEmail(BaseSubstitution):
    """ Move folder email substitution
    """
    category = u'AsyncMove'
    description = u'Move folder e-mail'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'asyncmove_email', '')


class AsyncMoveError(BaseSubstitution):
    """ error message substitution
    """
    category = u'AsyncMove'
    description = u'Error message'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'error', '')


class AsyncMoveJobID(BaseSubstitution):
    """ job id substitution
    """
    category = u'AsyncMove'
    description = u'Job ID'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.wrapper, 'job_id', '')


class AsyncMoveQueueLength(BaseSubstitution):
    """ Async queue length
    """
    category = u'AsyncMove'
    description = u'Queue length'

    def safe_call(self):
        """ Safe call
        """
        service = getUtility(IAsyncService)
        return len(service.getQueues()[''])

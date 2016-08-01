""" Public Interface
"""
from zope.interface import Interface


class IContextWrapper(Interface):
    """ Context wrapper used by async events
    """

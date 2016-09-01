""" Tests
"""
import unittest
from Testing import ZopeTestCase as ztc

from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
ptc.setupPloneSite()

import eea.asyncmove


class TestCase(ptc.PloneTestCase):
    """ Test case
    """
    class layer(PloneSite):
        """ Layer
        """
        @classmethod
        def setUp(cls):
            """ Setup
            """
            fiveconfigure.debug_mode = True
            ztc.installPackage(eea.asyncmove)
            fiveconfigure.debug_mode = False

        @classmethod
        def tearDown(cls):
            """ Tear down
            """
            pass


def test_suite():
    """ Test suite
    """
    return unittest.TestSuite([

        # Unit tests
        #doctestunit.DocFileSuite(
        #    'README.txt', package='eea.asyncmove',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

        #doctestunit.DocTestSuite(
        #    module='eea.asyncmove.mymodule',
        #    setUp=testing.setUp, tearDown=testing.tearDown),


        # Integration tests that use PloneTestCase
        #ztc.ZopeDocFileSuite(
        #    'README.txt', package='eea.asyncmove',
        #    test_class=TestCase),

        #ztc.FunctionalDocFileSuite(
        #    'browser.txt', package='eea.asyncmove',
        #    test_class=TestCase),

        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

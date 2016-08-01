from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='eea.asyncmove',
      version=version,
      description="package for moving of large folders",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        ],
      keywords='',
      author='European Environment Agency',
      author_email="webadmin@eea.europa.eu",
      url='http://eea.github.com/eea/eea.asyncmove',
      license='GPL version 2',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['eea'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'plone.api',
          'plone.app.async',
          'eea.converter'
      ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )

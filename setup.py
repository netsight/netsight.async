import sys

from setuptools import setup, find_packages

version = '1.0.0'

requirements = [
    'setuptools',
    'zope.component>=3.4.0',
    'zope.i18n>=3.4.0',
    'zope.i18nmessageid>=3.4.0',
    'Zope2>=2.8.0',
    'zope.publisher'
]

test_requirements = [
    'mock',
    'Products.PloneTestCase'
]

if sys.version_info[:3] < (2,6,0):
    requirements.append('simplejson')

setup(name='netsight.async',
      version=version,
      description="Provides a base view for running asynchronous "
                  "processes from Zope.",
      long_description='\n\n'.join([open(f).read() for f in [
                            "README.rst",
                            "HISTORY.rst",
                            'LICENSE.rst',
                             ]]),
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        ],
      keywords='Plone Zope Asynchronous Fork Process Task Browser View',
      author='Richard Mitchell',
      author_email='richard@netsight.co.uk',
      url='http://www.netsight.co.uk',
      license='TBD',
      
      
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['netsight'],
      include_package_data=True,
      zip_safe=False,
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      
      
      install_requires=requirements,
      setup_requires=[],
      tests_require=test_requirements,
      extras_require={
        'test': test_requirements
      },
      )

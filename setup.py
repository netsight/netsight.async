from setuptools import setup, find_packages

version = '0.0.1'

setup(name='netsight.async',
      version=version,
      description="Provides a base view for running asynchronous process.",
      long_description=open("README.rst").read() + "\n\n" +
                       open("HISTORY.rst").read(),
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        ],
      keywords='Plone Zope Asynchronous Fork Process Browser View',
      author='Richard Mitchell',
      author_email='richard@netsight.co.uk',
      url='http://www.netsight.co.uk',
      license='MIT',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['netsight'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      setup_requires=[],
      )

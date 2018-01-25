from setuptools import setup


setup(name='changify',
      version='0.1',
      description='Framework to aid in the use of LCMAP-pyccd with ARD',
      long_description='',

      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: Public Domain',
        'Programming Language :: Python :: 3.6',
      ],

      keywords='lcmap pyccd ccdc ard',
      url='https://github.com/klsmith-usgs/changify',
      author='Kelcy Smith',
      author_email='kelcy.smith.ctr@usgs.gov',
      license='Unlicense',

      install_requires=['numpy',
                        'pyyaml',
                        'lcmap-merlin',
                        'lcmap-pyccd'],

      extras_require={'test': ['pytest'],

                      'dev': [],

                      'doc': []},
      )

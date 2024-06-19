import setuptools

setuptools.setup(
    name='autolaunch',
    version="0.0.1.dev",
    url='https://github.com/tmcqueen-materials/autolaunch',
    license='GNU GPLv2',
    author='Tyrel M. McQueen',
    author_email='tmcqueen-pypi@demoivre.com',
    description='Jupyter Extension to automatically access and enable analysis of data stored at remote URLs',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    include_package_data=True,
    platforms='any',
    install_requires=['jupyter_server>=1.10.1', 'tornado'],
    data_files=[
        ('etc/jupyter/jupyter_server_config.d', ['autolaunch/etc/jupyter_server_config.d/autolaunch.json']),
        ('etc/jupyter/jupyter_notebook_config.d', ['autolaunch/etc/jupyter_notebook_config.d/autolaunch.json'])
    ],
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)

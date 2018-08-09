from setuptools import find_packages, setup

__version__ = '1.9'

setup(
    name='backopper',
    version=__version__,
    platforms=['any'],
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    py_modules=['backopper'],
    install_requires=[
        'python-crontab',
        'requests',
        'python-dotenv',
        'click',
        'arrow',
        'scp'
    ],
    entry_points='''
        [console_scripts]
        backopper=src.backopper:main
    ''',
    author='Alex Raileanu',
    author_email='alex@opper.nl',
)

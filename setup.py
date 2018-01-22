from setuptools import setup, find_packages

setup(
    name='backopper',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    py_modules=['backopper'],
    install_requires=[
        'python-crontab',
        'requests',
        'python-dotenv',
        'click'
    ],
    entry_points='''
        [console_scripts]
        backopper=src.backopper:main
    ''',
    author='Alex Raileanu',
    author_email='alex@opper.nl',
)

from setuptools import setup

setup(
    name='Betelgeuse',
    version='1.0',
    py_modules=['betelgeuse'],
    install_requires=['click', 'testimony'],
    entry_points='''
        [console_scripts]
        betelgeuse=betelgeuse:cli
    ''',
)

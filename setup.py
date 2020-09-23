from setuptools import setup, find_packages

install_requires = [l.split('#')[0].strip()
                    for l in open('requirements.txt').readlines()
                    if not l.startswith('#') and not l.startswith('-e')]
setup(
    name='domshot',
    version='0.1.6',
    packages = find_packages(),
    install_requires=install_requires,
)

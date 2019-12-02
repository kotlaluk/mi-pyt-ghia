from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = ''.join(f.readlines())

setup(
    name='ghia_kotlaluk',
    version='0.4',
    description='GitHub Issue Assigner',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Lukáš Kotlaba',
    author_email='lukas.kotlaba@gmail.com',
    keywords='ghia,github,issue,assigner',
    license='GNU GPLv3',
    url='https://github.com/kotlaluk/mi-pyt-ghia',
    packages=find_packages(),
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Version Control',
        'Topic :: Software Development :: Version Control :: Git'
        ],
    install_requires=['Flask', 'click', 'requests'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'betamax'],
    entry_points={
        'console_scripts': [
            'ghia = ghia.cli:cli',
        ],
    },
    package_data={'ghia': ['templates/*.html', 'static/*.css']},
    zip_safe=False,
)

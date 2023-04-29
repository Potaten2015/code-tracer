import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

REQUIREMENTS = [
    # Add your list of production dependencies here, eg:
    # 'requests == 2.*',
]

DEV_REQUIREMENTS = [
    'black == 22.*',
    'build == 0.7.*',
    'flake8 == 4.*',
    'isort == 5.*',
    'twine == 4.*',
]

setuptools.setup(
    name='code-tracer',
    version='0.1.0',
    description='Track Every Line of Code',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://github.com/Potaten2015/code-tracer',
    author='Potaten2015',
    license='MIT',
    packages=setuptools.find_packages(
        exclude=[
            'examples',
            'test',
        ]
    ),
    package_data={
        'code-tracer': [
            'py.typed',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=REQUIREMENTS,
    extras_require={
        'dev': DEV_REQUIREMENTS,
    },
    entry_points={
        'console_scripts': [
            'code-tracer=code_tracer.watch_directories:watch_directories',
        ]
    },
    python_requires='>=3.7, <4',
)

from setuptools import setup


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='Py Meta Utils',
    version='0.6.2',
    description='Metaclass utilities for Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/briancappello/py-meta-utils',
    author='Brian Cappello',
    license='MIT',

    py_modules=['py_meta_utils'],
    install_requires=[],
    extras_require={
        'docs': [
            'm2r',
            'sphinx',
            'sphinx-autobuild',
            'sphinx-rtd-theme',
        ],
    },
    python_requires='>=3.5',
    include_package_data=True,
    zip_safe=False,

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)

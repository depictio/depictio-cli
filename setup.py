from setuptools import setup, find_packages

setup(
    name="depictio-cli",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "colorlog",
        "httpx",
        "devtools",
        "polars",
        "deltalake",
        "fastexcel"
        "python-jose",
        "pyyaml",
        "tinydb",
        "typer",
        "typeguard",
        ###
        "depictio-models",
    ],
    entry_points={
        "console_scripts": [
            "depictio-cli=depictio_cli.depictio_cli:main"
        ]
    },
    author="Thomas Weber",
    author_email="thomas.weber@embl.de",
    description="Depictio CLI to interact with the Depictio API",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="http://github.com/depictio/depictio-cli",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)

import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="cryptocom-python",
    version="0.1.0",
    description="Python API wrapper for crypto.com/exchange",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/markoaurelije/crypto_com_API_python",
    author="Marko",
    author_email="markoaurelije@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6.5",
    ],
    packages=["cryptocom"],
    include_package_data=True,
    install_requires=["requests", ],
    entry_points={
    },
)
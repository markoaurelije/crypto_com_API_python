import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="cryptocom",
    version="0.2.4",
    description="Python API wrapper for crypto.com/exchange",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/markoaurelije/crypto_com_API_python",
    download_url="https://github.com/markoaurelije/crypto_com_API_python/dist/cryptocom-0.2.3.tar.gz",
    author="Marko",
    author_email="markoaurelije@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["cryptocom"],
    include_package_data=True,
    install_requires=["requests", ],
    entry_points={
    },
)

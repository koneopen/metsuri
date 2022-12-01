import setuptools
from pathlib import Path

here = Path(__file__).parent.resolve()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(here / "src" / "metsuri" / "VERSION", "r") as version_file:
    version = version_file.read().strip()


setuptools.setup(
    name="metsuri",
    version=version,
    author="Sami J. Lehtinen",
    author_email="sami.lehtinen@kone.com",
    description="Serial log collector and uploader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/koneopen/metsuri",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=["docopt>=0.6.2", "boto3>=1.16", "pyserial>=3.4",
                      "rich>=9.0"],
    extras_require={
        'dev': ["freezegun", "pytest", "tox", "tox-pyenv", "wheel"]
    },
    entry_points={
        'console_scripts': ["log-download=metsuri.log_download:main",
                            "log-uploader=metsuri.log_uploader:main",
                            "serial-logger=metsuri.serial_logger:main",
                            "log-check=metsuri.log_check:main",
                            "log-generate=metsuri.log_generate:main"]
    },
    package_data={
        "metsuri": ["VERSION"]
    }

)
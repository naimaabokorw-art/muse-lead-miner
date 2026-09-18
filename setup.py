from setuptools import setup, find_packages

setup(
    name="muse-lead-miner",
    version="0.1.0",
    description="Muse Web Studio lead intelligence system",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.3",
        "openpyxl>=3.1.2",
        "dnspython>=2.6.1",
        "pandas>=2.2.2",
        "pytest>=8.2.2",
    ],
)

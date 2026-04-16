"""
Setup script for Trading AI package.
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    with open("docs/README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="trading-ai",
    version="2.0.0",
    author="Trading AI Team",
    author_email="team@trading-ai.com",
    description="Institutional-Grade Trading Signal Engine",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Kamrad999/TRADING-AI",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "enhanced": [
            "aiohttp>=3.8.0",
            "asyncio-mqtt>=0.13.0",
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "python-dotenv>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "trading-ai=trading_ai.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "trading_ai": ["config/*.yaml", "data/*.json"],
    },
)

from setuptools import setup, find_packages

setup(
    name="git-query-service",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pygit2",
        "neo4j",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-cov",
            "httpx",
            "pytest-asyncio",
        ],
    },
) 
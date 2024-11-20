from setuptools import setup, find_packages

setup(
    name="git-query-service",
    version="0.1.1",
    packages=find_packages(where="git_query"),
    package_dir={"": "git_query"},
    install_requires=[
        "fastapi",
        "uvicorn",
        "pygit2",
    ],
    extras_require={
        "test": ["pytest", "httpx"],
    },
) 
from setuptools import setup, find_packages

setup(
    name="smartcrm",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask",
        "flask-sqlalchemy",
        "flask-migrate",
        "flask-cors",
        "psycopg2-binary",
        "alembic",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-cov",
            "pytest-flask",
            "pytest-sqlalchemy",
        ],
    },
)

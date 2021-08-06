from setuptools import find_packages, setup

setup(
    name="polycal",
    version="0.1.0",
    description="Google calendars aggregation tool",
    url="https://github.com/rooterkyberian/polycal",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    platforms="any",
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.9",
    install_requires=[
        "Click>=8",
        "coloredlogs",
        "dependency_injector",
        "google-api-python-client>=2",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "pydantic",
        "python-dateutil",
    ],
    entry_points={"console_scripts": ["polycal=polycal.cli:main"]},
    keywords=["calendar"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)

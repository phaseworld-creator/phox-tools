from setuptools import setup, find_packages

setup(
    name="phox-tools",
    version="1.0.0",
    description="A Swiss Army Knife for Hackers and Developers (zero dependencies)",
    author="Phox",
    packages=find_packages(),
    package_data={
        "phox": ["web/static/*.html", "web/static/*.css", "web/static/*.js"],
    },
    include_package_data=True,
    install_requires=[],
    entry_points={
        "console_scripts": [
            "phox=phox.cli:main",
        ],
    },
    python_requires=">=3.8",
)

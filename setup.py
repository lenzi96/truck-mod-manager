from setuptools import setup, find_packages

setup(
    name="truck-mod-manager",
    version="1.0.2",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "truck_mod_manager": ["resources/*"],
    },
    entry_points={
        "console_scripts": [
            "truck-mod-manager=truck_mod_manager.app:main",
        ],
    },
    install_requires=[
        "PyQt6>=6.4.0",
        "requests>=2.28.0",
    ],
)


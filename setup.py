from setuptools import setup, find_packages

setup(
    name="time-display-tool",
    version='1.0',
    # Modules to import from other scripts:
    packages=find_packages(),
    # Executables
    scripts=["main.py"],
)

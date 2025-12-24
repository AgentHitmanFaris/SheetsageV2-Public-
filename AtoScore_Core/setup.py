from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# Filter out git dependencies and comments for install_requires
install_requires = [
    req for req in requirements
    if req and not req.startswith("#") and not req.startswith("git+") and not req.startswith("-")
]

setup(
    name="sheetsage",
    packages=["sheetsage"],
    install_requires=install_requires,
)

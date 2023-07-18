import setuptools
import os


def read_requirements():
    filename = os.path.join(os.path.dirname(__file__), "requirements.txt")
    dependencis = []
    with open(filename) as file:
        for line in file.read().split("\n"):
            if line:
                dependencis.append(line)
    return dependencis


if __name__ == "__main__":
    setuptools.setup(
        name="bobaH_asyncio_protocols",
        version="1.0.1",
        description="Async http/socks4/socks5 connection protocols",
        package_dir={"": "src"},
        packages=setuptools.find_packages("src"),
        install_requires=read_requirements(),
        python_requires=">=3.8"
    )

"""
Setup script для timestamp_store с автоматической компиляцией C++
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.egg_info import egg_info


def get_library_name():
    """Получить имя библиотеки для текущей платформы"""
    system = platform.system()
    if system == "Windows":
        return "timestamp_store.dll"
    elif system == "Darwin":
        return "libtimestamp_store.dylib"
    else:
        return "libtimestamp_store.so"


def get_compiler_command():
    """Получить команду компиляции для текущей платформы"""
    system = platform.system()
    lib_name = get_library_name()

    # Путь к исходникам
    src_dir = Path(__file__).parent / "timestamp_store" / "src"
    cpp_file = src_dir / "timestamp_store.cpp"
    output_dir = Path(__file__).parent / "timestamp_store"
    output_file = output_dir / lib_name

    if system == "Windows":
        # Пробуем найти компилятор
        # Сначала MSVC
        if shutil.which("cl"):
            return [
                "cl", "/O2", "/LD", "/EHsc",
                "/std:c++17",
                str(cpp_file),
                f"/Fe:{output_file}"
            ]
        # Затем MinGW
        elif shutil.which("g++"):
            return [
                "g++", "-O3", "-std=c++17", "-shared",
                "-o", str(output_file),
                str(cpp_file)
            ]
        else:
            raise RuntimeError(
                "No C++ compiler found. Install Visual Studio Build Tools or MinGW."
            )

    elif system == "Darwin":
        # macOS - используем clang++ или g++
        compiler = "clang++" if shutil.which("clang++") else "g++"
        return [
            compiler, "-O3", "-std=c++17",
            "-shared", "-fPIC",
            "-o", str(output_file),
            str(cpp_file)
        ]

    else:
        # Linux
        return [
            "g++", "-O3", "-std=c++17",
            "-shared", "-fPIC",
            "-o", str(output_file),
            str(cpp_file)
        ]


def compile_cpp_library():
    """Скомпилировать C++ библиотеку"""
    lib_name = get_library_name()
    output_dir = Path(__file__).parent / "timestamp_store"
    output_file = output_dir / lib_name

    # Проверяем, есть ли уже скомпилированная библиотека
    if output_file.exists():
        print(f"Library {lib_name} already exists, skipping compilation")
        return

    print(f"Compiling C++ library: {lib_name}")

    try:
        cmd = get_compiler_command()
        print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout)

        if output_file.exists():
            print(f"Successfully compiled {lib_name}")
        else:
            raise RuntimeError(f"Compilation succeeded but {lib_name} not found")

    except subprocess.CalledProcessError as e:
        print(f"Compilation failed!")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        raise RuntimeError(f"Failed to compile C++ library: {e}")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"C++ compiler not found. Please install g++ or clang++.\n"
            f"Ubuntu/Debian: sudo apt install g++\n"
            f"macOS: xcode-select --install\n"
            f"Windows: Install Visual Studio Build Tools or MinGW"
        )


class BuildPyWithCompile(build_py):
    """Кастомная команда build_py с компиляцией C++"""

    def run(self):
        compile_cpp_library()
        super().run()

        # Копируем скомпилированную библиотеку в build директорию
        lib_name = get_library_name()
        src_lib = Path(__file__).parent / "timestamp_store" / lib_name

        if src_lib.exists():
            dest_dir = Path(self.build_lib) / "timestamp_store"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_lib = dest_dir / lib_name
            shutil.copy2(src_lib, dest_lib)
            print(f"Copied {lib_name} to {dest_lib}")


class DevelopWithCompile(develop):
    """Кастомная команда develop с компиляцией C++"""

    def run(self):
        compile_cpp_library()
        super().run()


class InstallWithCompile(install):
    """Кастомная команда install с компиляцией C++"""

    def run(self):
        compile_cpp_library()
        super().run()


class EggInfoWithCompile(egg_info):
    """Кастомная команда egg_info с компиляцией C++"""

    def run(self):
        compile_cpp_library()
        super().run()


setup(
    name="timestamp-store",
    version="1.0.0",
    description="Fast timestamp-based data structure with O(log N) operations",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/timestamp-store",
    packages=find_packages(),
    package_data={
        "timestamp_store": [
            "src/*.cpp",
            "*.so",
            "*.dylib",
            "*.dll",
        ],
    },
    include_package_data=True,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: C++",
    ],
    cmdclass={
        "build_py": BuildPyWithCompile,
        "develop": DevelopWithCompile,
        "install": InstallWithCompile,
        "egg_info": EggInfoWithCompile,
    },
)
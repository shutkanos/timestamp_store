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


def find_vswhere() -> Path | None:
    """Найти vswhere.exe для поиска Visual Studio"""
    vswhere_paths = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
    ]
    for path in vswhere_paths:
        if path.exists():
            return path
    return None


def find_msvc_vcvarsall() -> Path | None:
    """Найти vcvarsall.bat для настройки окружения MSVC"""
    # Способ 1: Через vswhere (рекомендуемый)
    vswhere = find_vswhere()
    if vswhere:
        try:
            result = subprocess.run(
                [
                    str(vswhere), "-latest", "-products", "*",
                    "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property", "installationPath"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                vcvarsall = (
                        Path(result.stdout.strip())
                        / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                )
                if vcvarsall.exists():
                    return vcvarsall
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Способ 2: Поиск в стандартных путях
    program_files_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    ]

    for pf in program_files_dirs:
        vs_base = Path(pf) / "Microsoft Visual Studio"
        if not vs_base.exists():
            continue

        for year in ["2022", "2019", "2017"]:
            for edition in ["Enterprise", "Professional", "Community", "BuildTools"]:
                vcvarsall = (
                        vs_base / year / edition
                        / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                )
                if vcvarsall.exists():
                    return vcvarsall

    return None


def find_mingw_gpp() -> Path | None:
    """Найти g++ от MinGW/MSYS2 на Windows"""
    # Способ 1: Проверяем PATH
    gpp = shutil.which("g++")
    if gpp:
        return Path(gpp)

    # Способ 2: Известные пути установки
    user_profile = os.environ.get("USERPROFILE", "")
    possible_paths = [
        # MSYS2 (наиболее популярный)
        Path(r"C:\msys64\mingw64\bin\g++.exe"),
        Path(r"C:\msys64\ucrt64\bin\g++.exe"),
        Path(r"C:\msys64\clang64\bin\g++.exe"),
        Path(r"C:\msys64\mingw32\bin\g++.exe"),
        # Standalone MinGW-w64
        Path(r"C:\mingw64\bin\g++.exe"),
        Path(r"C:\mingw32\bin\g++.exe"),
        # Старый MinGW
        Path(r"C:\MinGW\bin\g++.exe"),
        # Chocolatey
        Path(r"C:\tools\mingw64\bin\g++.exe"),
        Path(r"C:\ProgramData\chocolatey\lib\mingw\tools\install\mingw64\bin\g++.exe"),
        # Scoop
        Path(user_profile) / r"scoop\apps\mingw\current\bin\g++.exe",
        # WinLibs
        Path(r"C:\mingw-w64\bin\g++.exe"),
    ]

    # Добавляем пути из Program Files
    for pf_var in ["ProgramFiles", "ProgramFiles(x86)"]:
        pf = os.environ.get(pf_var, "")
        if pf:
            possible_paths.extend([
                Path(pf) / r"mingw-w64\x86_64-posix-seh\mingw64\bin\g++.exe",
                Path(pf) / r"mingw64\bin\g++.exe",
                Path(pf) / r"CodeBlocks\MinGW\bin\g++.exe",
            ])

    for path in possible_paths:
        if path.exists():
            return path

    return None


def get_compiler_command() -> list[str]:
    """Получить команду компиляции для текущей платформы"""
    system = platform.system()
    lib_name = get_library_name()

    # Путь к исходникам
    src_dir = Path(__file__).parent / "timestamp_store" / "src"
    cpp_file = src_dir / "timestamp_store.cpp"
    output_dir = Path(__file__).parent / "timestamp_store"
    output_file = output_dir / lib_name

    if system == "Windows":
        # Вариант 1: cl в PATH (запущено из Developer Command Prompt)
        if shutil.which("cl"):
            return [
                "cl", "/O2", "/LD", "/EHsc",
                "/std:c++17",
                str(cpp_file),
                f"/Fe:{output_file}"
            ]

        # Вариант 2: g++ (MinGW/MSYS2)
        gpp = find_mingw_gpp()
        if gpp:
            return [
                str(gpp), "-O3", "-std=c++17", "-shared",
                "-o", str(output_file),
                str(cpp_file)
            ]

        # Вариант 3: MSVC через vcvarsall.bat
        vcvarsall = find_msvc_vcvarsall()
        if vcvarsall:
            arch = "x64" if platform.machine().endswith('64') else "x86"
            compile_cmd = (
                f'cl /O2 /LD /EHsc /std:c++17 '
                f'"{cpp_file}" /Fe:"{output_file}"'
            )
            return [
                "cmd", "/c",
                f'call "{vcvarsall}" {arch} >nul 2>&1 && {compile_cmd}'
            ]

        raise RuntimeError(
            "No C++ compiler found on Windows.\n\n"
            "Install one of:\n"
            "  • MSYS2 MinGW: https://www.msys2.org/\n"
            "    Then run: pacman -S mingw-w64-x86_64-gcc\n"
            "  • Visual Studio Build Tools: "
            "https://visualstudio.microsoft.com/visual-cpp-build-tools/\n"
            "    Select 'Desktop development with C++'"
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
    author='Shutkanos',
    author_email='Shutkanos836926@mail.ru',
    url="https://github.com/shutkanos/timestamp_store",
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
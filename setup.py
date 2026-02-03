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
    system = platform.system()
    if system == "Windows":
        return "timestamp_store.dll"
    elif system == "Darwin":
        return "libtimestamp_store.dylib"
    else:
        return "libtimestamp_store.so"


def find_mingw_path():
    mingw_search_paths = [
        Path("C:/msys64/mingw64/bin"),
        Path("C:/msys64/ucrt64/bin"),
        Path("C:/msys64/clang64/bin"),
        Path("C:/msys64/mingw32/bin"),
        Path("C:/msys2/mingw64/bin"),
        Path("C:/msys2/ucrt64/bin"),
        Path("C:/mingw64/bin"),
        Path("C:/mingw/bin"),
        Path("C:/MinGW/bin"),
        Path("C:/tools/mingw64/bin"),
        Path(os.environ.get("USERPROFILE", "")) / "scoop/apps/mingw/current/bin",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "mingw-w64/x86_64-8.1.0-posix-seh-rt_v6-rev0/mingw64/bin",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "mingw64/bin",
    ]

    for env_var in ["MINGW_HOME", "MINGW64_HOME", "MSYS2_HOME"]:
        if env_var in os.environ:
            env_path = Path(os.environ[env_var])
            if (env_path / "bin" / "g++.exe").exists():
                mingw_search_paths.insert(0, env_path / "bin")
            elif (env_path / "g++.exe").exists():
                mingw_search_paths.insert(0, env_path)

    for path in mingw_search_paths:
        if path.exists() and (path / "g++.exe").exists():
            print(f"Found MinGW at: {path}")
            return path

    return None


def find_msvc_vcvarsall():
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")

    vswhere_paths = [
        Path(program_files_x86) / "Microsoft Visual Studio/Installer/vswhere.exe",
        Path(program_files) / "Microsoft Visual Studio/Installer/vswhere.exe",
    ]

    vswhere = None
    for p in vswhere_paths:
        if p.exists():
            vswhere = p
            break

    if vswhere:
        try:
            result = subprocess.run(
                [
                    str(vswhere),
                    "-latest",
                    "-property", "installationPath",
                    "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            vs_path = Path(result.stdout.strip())
            vcvarsall = vs_path / "VC/Auxiliary/Build/vcvarsall.bat"
            if vcvarsall.exists():
                print(f"Found MSVC vcvarsall at: {vcvarsall}")
                return vcvarsall
        except subprocess.CalledProcessError:
            pass

    vs_years = ["2022", "2019", "2017"]
    vs_editions = ["Enterprise", "Professional", "Community", "BuildTools"]

    for year in vs_years:
        for edition in vs_editions:
            for pf in [program_files, program_files_x86]:
                vcvarsall = Path(pf) / f"Microsoft Visual Studio/{year}/{edition}/VC/Auxiliary/Build/vcvarsall.bat"
                if vcvarsall.exists():
                    print(f"Found MSVC vcvarsall at: {vcvarsall}")
                    return vcvarsall

    return None


def get_msvc_environment(vcvarsall):
    arch = "x64" if platform.machine().endswith('64') else "x86"

    cmd = f'"{vcvarsall}" {arch} >nul 2>&1 && set'

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )

        env = {}
        for line in result.stdout.splitlines():
            if '=' in line:
                key, _, value = line.partition('=')
                env[key] = value

        return env
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to setup MSVC environment: {e}")
        return None


def get_compiler_command():
    system = platform.system()
    lib_name = get_library_name()

    src_dir = Path(__file__).parent / "timestamp_store" / "src"
    cpp_file = src_dir / "timestamp_store.cpp"
    output_dir = Path(__file__).parent / "timestamp_store"
    output_file = output_dir / lib_name

    env = os.environ.copy()

    if system == "Windows":
        mingw_path = find_mingw_path()
        if mingw_path:
            env["PATH"] = str(mingw_path) + os.pathsep + env.get("PATH", "")

            gpp_path = mingw_path / "g++.exe"

            return [
                str(gpp_path),
                "-O3", "-std=c++17", "-shared",
                "-static-libgcc",
                "-static-libstdc++",
                "-static",
                "-o", str(output_file),
                str(cpp_file)
            ], env

        vcvarsall = find_msvc_vcvarsall()
        if vcvarsall:
            msvc_env = get_msvc_environment(vcvarsall)
            if msvc_env:
                return [
                    "cl",
                    "/O2",
                    "/LD",
                    "/EHsc",
                    "/std:c++17",
                    "/MT",
                    str(cpp_file),
                    f"/Fe:{output_file}",
                    f"/Fo:{output_dir}\\",
                ], msvc_env

        if shutil.which("g++"):
            print("Using g++ from PATH")
            return [
                "g++", "-O3", "-std=c++17", "-shared",
                "-static-libgcc", "-static-libstdc++",
                "-o", str(output_file),
                str(cpp_file)
            ], env

        if shutil.which("cl"):
            print("Using cl from PATH")
            return [
                "cl", "/O2", "/LD", "/EHsc",
                "/std:c++17", "/MT",
                str(cpp_file),
                f"/Fe:{output_file}"
            ], env
        raise RuntimeError(
            "No C++ compiler found on Windows!\n\n"
            "Please install one of the following:\n"
            "1. MSYS2 MinGW: https://www.msys2.org/\n"
            "   Then run: pacman -S mingw-w64-x86_64-gcc\n\n"
            "2. Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/\n"
            "   Select 'Desktop development with C++'\n\n"
            "3. Standalone MinGW-w64: https://www.mingw-w64.org/downloads/"
        )

    elif system == "Darwin":
        compiler = "clang++" if shutil.which("clang++") else "g++"
        return [
            compiler, "-O3", "-std=c++17",
            "-shared", "-fPIC",
            "-o", str(output_file),
            str(cpp_file)
        ], env

    else:
        if not shutil.which("g++"):
            raise RuntimeError(
                "g++ not found. Please install:\n"
                "Ubuntu/Debian: sudo apt install g++\n"
                "Fedora: sudo dnf install gcc-c++\n"
                "Arch: sudo pacman -S gcc"
            )
        return [
            "g++", "-O3", "-std=c++17",
            "-shared", "-fPIC",
            "-o", str(output_file),
            str(cpp_file)
        ], env


def compile_cpp_library():
    lib_name = get_library_name()
    output_dir = Path(__file__).parent / "timestamp_store"
    output_file = output_dir / lib_name

    if output_file.exists():
        print(f"Library {lib_name} already exists, skipping compilation")
        return

    print(f"Compiling C++ library: {lib_name}")
    print(f"Platform: {platform.system()} {platform.machine()}")

    try:
        cmd, env = get_compiler_command()
        print(f"Running: {' '.join(cmd)}")

        path_preview = env.get("PATH", "").split(os.pathsep)[:3]
        print(f"PATH preview: {path_preview}")

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(output_dir)
        )

        if result.stdout:
            print(result.stdout)

        if output_file.exists():
            print(f"Successfully compiled {lib_name}")
            print(f"Library size: {output_file.stat().st_size} bytes")
        else:
            raise RuntimeError(f"Compilation succeeded but {lib_name} not found")

    except subprocess.CalledProcessError as e:
        print(f"Compilation failed!")
        print(f"Command: {' '.join(cmd)}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        raise RuntimeError(f"Failed to compile C++ library: {e}")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"C++ compiler not found: {e}\n"
            f"Please install g++, clang++, or MSVC."
        )
    finally:
        if platform.system() == "Windows":
            for ext in [".obj", ".exp", ".lib"]:
                for f in output_dir.glob(f"*{ext}"):
                    try:
                        f.unlink()
                    except:
                        pass


class BuildPyWithCompile(build_py):
    def run(self):
        compile_cpp_library()
        super().run()

        lib_name = get_library_name()
        src_lib = Path(__file__).parent / "timestamp_store" / lib_name

        if src_lib.exists():
            dest_dir = Path(self.build_lib) / "timestamp_store"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_lib = dest_dir / lib_name
            shutil.copy2(src_lib, dest_lib)
            print(f"Copied {lib_name} to {dest_lib}")


class DevelopWithCompile(develop):
    def run(self):
        compile_cpp_library()
        super().run()


class InstallWithCompile(install):
    def run(self):
        compile_cpp_library()
        super().run()


class EggInfoWithCompile(egg_info):
    def run(self):
        compile_cpp_library()
        super().run()

long_description = ""
if os.path.exists("README.md"):
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="timestamp-store",
    version="1.0.0",
    description="Fast timestamp-based data structure with O(log N) operations",
    long_description=long_description,
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
        "Operating System :: OS Independent",
    ],
    cmdclass={
        "build_py": BuildPyWithCompile,
        "develop": DevelopWithCompile,
        "install": InstallWithCompile,
        "egg_info": EggInfoWithCompile,
    },
)
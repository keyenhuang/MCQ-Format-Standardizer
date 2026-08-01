"""
PyInstaller Packaging Script for MCQ Format Standardizer.

Usage:
    python build_exe.py
"""

import os
import subprocess
import sys


def build():
    print("Building MCQ Format Standardizer executable...")

    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        add_data_ctk = f"{ctk_path}{os.pathsep}customtkinter/"
    except ImportError:
        print("Error: customtkinter is not installed. Please install requirements.txt first.")
        sys.exit(1)

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=MCQFormatStandardizer",
        f"--add-data={add_data_ctk}",
        "main.py"
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\nBuild successful! Output executable is located in dist/MCQFormatStandardizer/")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")


if __name__ == "__main__":
    build()

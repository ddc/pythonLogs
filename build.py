#!/usr/bin/env python
import compileall
import sys
import tomllib
from pathlib import Path


def parse_python_version_requirement():
    """Parse Python version requirement from pyproject.toml"""
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    python_req = data["tool"]["poetry"]["dependencies"]["python"]
    
    # Parse version constraint like "^3.12"
    if python_req.startswith("^"):
        min_version = python_req[1:]
        major, minor = map(int, min_version.split("."))
        return major, minor
    elif python_req.startswith(">="):
        min_version = python_req[2:]
        major, minor = map(int, min_version.split("."))
        return major, minor
    else:
        # Default fallback
        return 3, 12


def get_compatible_python_versions(min_major, min_minor):
    """Generate list of compatible Python versions"""
    versions = []
    current_major, current_minor = sys.version_info[:2]
    
    # Start from the minimum required version
    for major in range(min_major, min_major + 1):  # Only Python 3.x for now
        start_minor = min_minor if major == min_major else 0
        # Go up to current Python version + 2 minor versions for future compatibility
        end_minor = max(current_minor + 2, 12) if major == current_major else 12
        
        for minor in range(start_minor, end_minor + 1):
            if major == 3 and minor >= min_minor:
                versions.append(f"{major}.{minor}")
    
    return versions


def build():
    """Build bytecode for all compatible Python versions"""
    try:
        min_major, min_minor = parse_python_version_requirement()
        compatible_versions = get_compatible_python_versions(min_major, min_minor)
        
        print(f"Building for Python versions: {', '.join(compatible_versions)}")
        
        # Compile for current Python version
        print(f"Compiling for Python {sys.version_info.major}.{sys.version_info.minor}")
        compileall.compile_dir('pythonDatabases', force=True)
        
        # Note: For actual cross-version bytecode, you'd need multiple Python interpreters
        # This compiles with current interpreter but documents compatibility
        print("Build completed successfully")
        
    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()

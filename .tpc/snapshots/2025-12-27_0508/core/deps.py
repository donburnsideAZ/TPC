"""
Dependency Detective for TPC.

Scans Python files to find import statements, then figures out
which ones are third-party packages (not stdlib, not local).

The goal: give users a clean list of what they need to pip install
before their project will run - without them having to think about it.
"""

import ast
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# Python standard library modules (3.10+)
# This list covers the vast majority - we can expand as needed
STDLIB_MODULES = frozenset({
    # Built-in and core
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2",
    
    # C
    "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code",
    "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
    
    # D-E
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "distutils", "doctest", "email", "encodings", "enum", "errno",
    
    # F-G
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "grp", "gzip",
    
    # H-I
    "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
    "itertools",
    
    # J-L
    "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma",
    
    # M-N
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers",
    
    # O-P
    "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb",
    "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
    "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
    
    # R
    "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy",
    
    # S
    "sched", "secrets", "select", "selectors", "shelve", "shlex",
    "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat",
    "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog",
    
    # T
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
    "textwrap", "threading", "time", "timeit", "tkinter", "token",
    "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty",
    "turtle", "turtledemo", "types", "typing",
    
    # U-Z
    "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile",
    "zipimport", "zlib", "zoneinfo",
    
    # Underscore prefixed (internal)
    "_thread", "__future__",
})


# macOS framework imports via pyobjc that look like packages but aren't pip-installable
# These get imported as "from Foundation import ..." but Foundation itself isn't the package
# The actual pip package is pyobjc-framework-Cocoa (which provides Foundation, AppKit, etc.)
MACOS_FRAMEWORKS = frozenset({
    'Foundation',
    'AppKit', 
    'Cocoa',
    'CoreFoundation',
    'CoreServices',
    'CoreGraphics',
    'CoreText',
    'CoreData',
    'Security',
    'SystemConfiguration',
    'IOKit',
    'Quartz',
    'WebKit',
    'ScriptingBridge',
    'AVFoundation',
    'CoreMedia',
    'CoreAudio',
    'AudioToolbox',
    'Metal',
    'MetalKit',
    'GameplayKit',
    'SpriteKit',
    'SceneKit',
    'MapKit',
    'EventKit',
    'Contacts',
    'Photos',
    'MediaPlayer',
    'StoreKit',
    'objc',  # pyobjc base module
    'PyObjCTools',
})


# Map import names to pip package names where they differ
# This is critical for packages where "import X" requires "pip install Y"
IMPORT_TO_PIP = {
    # Image/Graphics
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "skimage": "scikit-image",
    
    # Data Science
    "sklearn": "scikit-learn",
    "Bio": "biopython",
    
    # Config/Serialization
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    
    # Web/Parsing
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    
    # GUI
    "gi": "PyGObject",
    "OpenGL": "PyOpenGL",
    "wx": "wxPython",
    
    # Hardware/Serial
    "serial": "pyserial",
    "usb": "pyusb",
    
    # Crypto/Security
    "Crypto": "pycryptodome",
    "jose": "python-jose",
    "jwt": "PyJWT",
    
    # Misc
    "magic": "python-magic",
    
    # GUI extras
    "customtkinter": "customtkinter",  # Often missed by scanners due to conditional imports
    "CTk": "customtkinter",  # Alias some people use
    
    # Document handling
    "docx": "python-docx",
    "pptx": "python-pptx",
    "xlsx": "openpyxl",  # Common xlsx handler
    
    # Windows-specific (pywin32 bundle)
    # All these imports come from: pip install pywin32
    "win32api": "pywin32",
    "win32com": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "win32print": "pywin32",
    "win32process": "pywin32",
    "win32security": "pywin32",
    "win32service": "pywin32",
    "win32event": "pywin32",
    "win32file": "pywin32",
    "win32pipe": "pywin32",
    "win32ts": "pywin32",
    "win32net": "pywin32",
    "win32wnet": "pywin32",
    "win32crypt": "pywin32",
    "win32clipboard": "pywin32",
    "win32timezone": "pywin32",
    "pywintypes": "pywin32",
    "pythoncom": "pywin32",
    "servicemanager": "pywin32",
    "winerror": "pywin32",
    "mmapfile": "pywin32",
    "odbc": "pywin32",
    "dbi": "pywin32",
    "win32ui": "pywin32",
    "win32uiole": "pywin32",
    "pywin": "pywin32",
    "adodbapi": "pywin32",
    "isapi": "pywin32",
    "win32comext": "pywin32",
}


@dataclass
class ImportInfo:
    """Information about a single import."""
    module: str           # Top-level module name (e.g., "PyQt6" from "PyQt6.QtWidgets")
    full_import: str      # Full import path as written
    source_file: Path     # Which .py file this came from
    line_number: int      # Line number in source
    is_from_import: bool  # True for "from x import y", False for "import x"


@dataclass 
class ScanResult:
    """Results from scanning a project for dependencies."""
    
    # All imports found, grouped by top-level module
    imports: dict[str, list[ImportInfo]] = field(default_factory=dict)
    
    # Just the third-party packages (what you'd pip install)
    third_party: set[str] = field(default_factory=set)
    
    # Standard library modules that were imported
    stdlib: set[str] = field(default_factory=set)
    
    # Local imports (relative imports or project modules)
    local: set[str] = field(default_factory=set)
    
    # Files that couldn't be parsed (syntax errors, etc.)
    errors: dict[Path, str] = field(default_factory=dict)
    
    # Files that were scanned successfully
    scanned_files: list[Path] = field(default_factory=list)
    
    def summary(self) -> str:
        """Human-readable summary of the scan."""
        lines = []
        lines.append(f"Scanned {len(self.scanned_files)} Python file(s)")
        
        if self.errors:
            lines.append(f"⚠️  {len(self.errors)} file(s) had errors")
        
        if self.third_party:
            lines.append(f"\n📦 Third-party packages ({len(self.third_party)}):")
            for pkg in sorted(self.third_party):
                lines.append(f"   • {pkg}")
        else:
            lines.append("\n✓ No third-party dependencies detected")
        
        if self.stdlib:
            lines.append(f"\n📚 Standard library ({len(self.stdlib)}): {', '.join(sorted(self.stdlib))}")
        
        if self.local:
            lines.append(f"\n📁 Local imports ({len(self.local)}): {', '.join(sorted(self.local))}")
        
        return "\n".join(lines)
    
    def get_pip_packages(self) -> set[str]:
        """
        Get the actual pip package names for third-party imports.
        
        Applies IMPORT_TO_PIP mapping and deduplicates
        (e.g., win32api + win32com + pywintypes all become just 'pywin32')
        """
        pip_packages = set()
        for imp in self.third_party:
            pip_name = IMPORT_TO_PIP.get(imp, imp)
            pip_packages.add(pip_name)
        return pip_packages


class DependencyDetective:
    """
    Scans Python projects to find their dependencies.
    
    Usage:
        detective = DependencyDetective()
        result = detective.scan_project(Path("/path/to/project"))
        print(result.third_party)  # {'PyQt6', 'requests', ...}
    """
    
    def __init__(self):
        self.stdlib = STDLIB_MODULES
    
    def scan_project(self, project_path: Path, main_file: Optional[str] = None) -> ScanResult:
        """
        Scan a project directory for Python dependencies.
        
        Args:
            project_path: Root directory of the project
            main_file: Optional main file name to prioritize
            
        Returns:
            ScanResult with categorized imports
        """
        result = ScanResult()
        
        # Find all Python files
        py_files = list(project_path.rglob("*.py"))
        
        # Skip common non-project directories
        skip_dirs = {".git", ".tpc", ".ptc", "__pycache__", "venv", ".venv", 
                     "env", ".env", "build", "dist", ".eggs", "*.egg-info"}
        
        py_files = [
            f for f in py_files 
            if not any(skip in f.parts for skip in skip_dirs)
        ]
        
        # Collect all local module names (so we can exclude them from third-party)
        local_modules = self._find_local_modules(project_path, py_files)
        
        # Scan each file
        for py_file in py_files:
            try:
                imports = self._scan_file(py_file)
                result.scanned_files.append(py_file)
                
                for imp in imports:
                    # Add to the full imports dict
                    if imp.module not in result.imports:
                        result.imports[imp.module] = []
                    result.imports[imp.module].append(imp)
                    
                    # Categorize
                    if imp.module in self.stdlib:
                        result.stdlib.add(imp.module)
                    elif imp.module in MACOS_FRAMEWORKS:
                        # Skip macOS frameworks - they come from pyobjc, not pip directly
                        pass
                    elif imp.module in local_modules or imp.full_import.startswith("."):
                        result.local.add(imp.module)
                    else:
                        result.third_party.add(imp.module)
                        
            except SyntaxError as e:
                result.errors[py_file] = f"Syntax error: {e}"
            except Exception as e:
                result.errors[py_file] = str(e)
        
        return result
    
    def scan_file(self, file_path: Path) -> ScanResult:
        """Scan a single Python file for dependencies."""
        result = ScanResult()
        
        try:
            imports = self._scan_file(file_path)
            result.scanned_files.append(file_path)
            
            for imp in imports:
                if imp.module not in result.imports:
                    result.imports[imp.module] = []
                result.imports[imp.module].append(imp)
                
                if imp.module in self.stdlib:
                    result.stdlib.add(imp.module)
                elif imp.module in MACOS_FRAMEWORKS:
                    # Skip macOS frameworks - they come from pyobjc, not pip directly
                    pass
                elif imp.full_import.startswith("."):
                    result.local.add(imp.module)
                else:
                    # Can't know for sure if it's local without project context
                    result.third_party.add(imp.module)
                    
        except SyntaxError as e:
            result.errors[file_path] = f"Syntax error: {e}"
        except Exception as e:
            result.errors[file_path] = str(e)
        
        return result
    
    def _scan_file(self, file_path: Path) -> list[ImportInfo]:
        """Parse a Python file and extract all imports."""
        imports = []
        
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = self._get_top_level_module(alias.name)
                    imports.append(ImportInfo(
                        module=module,
                        full_import=alias.name,
                        source_file=file_path,
                        line_number=node.lineno,
                        is_from_import=False
                    ))
                    
            elif isinstance(node, ast.ImportFrom):
                # node.level > 0 means relative import (from . or from .. etc)
                if node.level > 0:
                    # Relative import - always local
                    prefix = "." * node.level
                    full = prefix + (node.module or "")
                    imports.append(ImportInfo(
                        module=".",  # Mark as relative
                        full_import=full,
                        source_file=file_path,
                        line_number=node.lineno,
                        is_from_import=True
                    ))
                elif node.module:
                    # Absolute import: from x.y import z
                    module = self._get_top_level_module(node.module)
                    imports.append(ImportInfo(
                        module=module,
                        full_import=node.module,
                        source_file=file_path,
                        line_number=node.lineno,
                        is_from_import=True
                    ))
        
        return imports
    
    def _get_top_level_module(self, module_name: str) -> str:
        """Extract the top-level module from a dotted path."""
        if module_name.startswith("."):
            return "."
        return module_name.split(".")[0]
    
    def _find_local_modules(self, project_path: Path, py_files: list[Path]) -> set[str]:
        """
        Identify modules that are part of this project.
        
        These are Python files/packages within the project that shouldn't
        be treated as third-party dependencies.
        """
        local = set()
        
        for py_file in py_files:
            # The file itself (minus .py extension) is a module
            rel_path = py_file.relative_to(project_path)
            
            # Top-level .py files
            if len(rel_path.parts) == 1:
                local.add(py_file.stem)
            
            # Packages (directories with __init__.py are importable)
            # Add each directory component as a potential local module
            for i, part in enumerate(rel_path.parts[:-1]):
                local.add(part)
        
        return local


def generate_requirements(result: ScanResult, include_versions: bool = False) -> str:
    """
    Generate a requirements.txt from scan results.
    
    Args:
        result: ScanResult from scanning
        include_versions: If True, try to get installed versions (future)
        
    Returns:
        String content for requirements.txt
    """
    lines = [
        "# Generated by TPC - Track Pack Click",
        "# Review and adjust versions as needed",
        ""
    ]
    
    # Use get_pip_packages() to get deduplicated pip names
    for pkg in sorted(result.get_pip_packages()):
        lines.append(pkg)
    
    return "\n".join(lines)


def parse_requirements(requirements_path: Path) -> set[str]:
    """
    Parse a requirements.txt file and extract package names.
    
    Handles:
    - Comments (#)
    - Version specifiers (==, >=, etc.)
    - Extras ([dev])
    - Git URLs (git+https://...)
    """
    packages = set()
    
    if not requirements_path.exists():
        return packages
    
    for line in requirements_path.read_text().splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        
        # Skip git URLs and other special entries
        if line.startswith(("-", "git+", "http://", "https://")):
            continue
        
        # Remove inline comments
        if " #" in line:
            line = line.split(" #")[0].strip()
        
        # Remove extras like [dev]
        if "[" in line:
            line = line.split("[")[0]
        
        # Remove version specifiers
        for sep in ["==", ">=", "<=", "!=", "~=", ">", "<"]:
            if sep in line:
                line = line.split(sep)[0]
                break
        
        # Normalize to lowercase for comparison
        pkg = line.strip().lower()
        if pkg:
            packages.add(pkg)
    
    return packages


@dataclass
class RequirementsComparison:
    """Comparison between detected dependencies and requirements.txt."""
    
    # Packages in requirements.txt
    in_requirements: set[str]
    
    # Packages detected by scanning
    detected: set[str]
    
    # Detected but not in requirements (need to add)
    missing_from_requirements: set[str]
    
    # In requirements but not detected (maybe unused?)
    extra_in_requirements: set[str]
    
    # In both
    matched: set[str]
    
    def summary(self) -> str:
        lines = []
        
        if self.missing_from_requirements:
            lines.append(f"⚠️  Missing from requirements.txt ({len(self.missing_from_requirements)}):")
            for pkg in sorted(self.missing_from_requirements):
                lines.append(f"   + {pkg}")
        
        if self.extra_in_requirements:
            lines.append(f"\n❓ In requirements.txt but not detected ({len(self.extra_in_requirements)}):")
            for pkg in sorted(self.extra_in_requirements):
                lines.append(f"   ? {pkg}")
            lines.append("   (These might be indirect dependencies or unused)")
        
        if self.matched:
            lines.append(f"\n✓ Matched ({len(self.matched)}): {', '.join(sorted(self.matched))}")
        
        if not self.missing_from_requirements and not self.extra_in_requirements:
            lines.append("✓ requirements.txt is in sync with your imports!")
        
        return "\n".join(lines)


def compare_requirements(result: ScanResult, requirements_path: Path) -> RequirementsComparison:
    """
    Compare detected dependencies against an existing requirements.txt.
    
    Returns a comparison showing what's missing, extra, and matched.
    """
    existing = parse_requirements(requirements_path)
    
    # Get deduplicated pip package names
    detected = {p.lower() for p in result.get_pip_packages()}
    
    # Also lowercase the existing set for comparison
    existing_lower = {p.lower() for p in existing}
    
    missing = detected - existing_lower
    extra = existing_lower - detected
    matched = detected & existing_lower
    
    return RequirementsComparison(
        in_requirements=existing,
        detected=detected,
        missing_from_requirements=missing,
        extra_in_requirements=extra,
        matched=matched
    )


# === Quick test ===
if __name__ == "__main__":
    # Test on the TPC project itself
    detective = DependencyDetective()
    
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(__file__).parent.parent
    
    print(f"Scanning: {path}\n")
    result = detective.scan_project(path)
    print(result.summary())
    
    print("\n--- Pip packages needed ---")
    for pkg in sorted(result.get_pip_packages()):
        print(f"  {pkg}")
    
    print("\n--- requirements.txt ---")
    print(generate_requirements(result))

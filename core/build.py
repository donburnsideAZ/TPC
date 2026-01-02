"""
Build Orchestrator for TPC.

Wraps PyInstaller to create distributable executables.
Users click Build, we handle the rest.

Outputs go to: ProjectFolder/TPC Builds/
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime

from .venv import EnvironmentWrangler


def _subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = 0x08000000
    return kwargs


@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    message: str
    output_path: Optional[Path] = None
    details: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class BuildProgress:
    """Progress update during build."""
    stage: str  # 'preparing', 'analyzing', 'building', 'packaging', 'done', 'failed'
    message: str
    percent: int = 0  # 0-100


# Common packages that need hidden imports
HIDDEN_IMPORTS = {
    'PyQt6': [
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
    ],
    'PyQt5': [
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    'PIL': [
        'PIL._tkinter_finder',
    ],
    'Pillow': [
        'PIL._tkinter_finder',
    ],
    'cryptography': [
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.backends.openssl',
    ],
    'requests': [
        'urllib3',
        'chardet',
        'certifi',
    ],
    'pandas': [
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
    ],
    'numpy': [
        'numpy.core._methods',
        'numpy.lib.format',
    ],
    'cv2': [
        'cv2.cv2',
    ],
    'sklearn': [
        'sklearn.utils._typedefs',
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._quad_tree',
        'sklearn.tree._utils',
    ],
}

# Data files that commonly need to be included
DATAS_PATTERNS = {
    'certifi': 'certifi:certifi',
}

# Packages that need --collect-all (bundles all data files, binaries, submodules)
# These have assets that PyInstaller doesn't find automatically
COLLECT_ALL_PACKAGES = [
    'whisper',         # mel_filters.npz and other model assets
    'openai_whisper',  # alternate whisper package name
    'torch',           # PyTorch native libraries (CRITICAL for whisper/ML apps)
    'torchaudio',      # Audio processing for torch
    'torchvision',     # Vision processing for torch (if used)
    'tkinterdnd2',     # native tkdnd library files
    'customtkinter',   # themes, images, and widget assets
    'CTkMessagebox',   # customtkinter extension with assets
    'numpy',           # Sometimes needs collect-all for full functionality
    'scipy',           # Scientific computing with native libs
]

# macOS framework imports that look like packages but aren't pip-installable
# These come from pyobjc and should be filtered from dependency scanning
MACOS_FRAMEWORKS = {
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
}


class BuildOrchestrator:
    """
    Manages PyInstaller builds for TPC projects.
    
    Usage:
        orchestrator = BuildOrchestrator()
        
        # Check if we can build
        if orchestrator.can_build_for_current_platform():
            result = orchestrator.build(
                project_path=Path("/path/to/project"),
                project_name="MyApp",
                main_file="main.py",
                onefile=True,
                windowed=True,
                icon_path=Path("icon.icns"),
                progress_callback=my_callback
            )
    """
    
    def __init__(self):
        self.system = platform.system()
        self.wrangler = EnvironmentWrangler()
    
    def can_build_for_current_platform(self) -> bool:
        """Check if we can build for the current platform."""
        return self.system in ("Darwin", "Windows", "Linux")
    
    def get_platform_name(self) -> str:
        """Get a friendly name for the current platform."""
        names = {
            "Darwin": "Mac",
            "Windows": "Windows", 
            "Linux": "Linux"
        }
        return names.get(self.system, self.system)
    
    def get_output_extension(self) -> str:
        """Get the executable extension for the current platform."""
        if self.system == "Windows":
            return ".exe"
        elif self.system == "Darwin":
            return ".app"
        else:
            return ""  # Linux has no extension
    
    def _get_build_dir(self, project_path: Path) -> Path:
        """Get the TPC Builds directory for a project."""
        return project_path / "TPC Builds"
    
    def _ensure_pyinstaller(self, project_name: str) -> tuple[bool, str]:
        """
        Ensure PyInstaller is installed in the project's venv.
        
        Returns (success, message).
        """
        if not self.wrangler.venv_exists(project_name):
            return False, "No environment exists. Set up the environment first."
        
        pip_path = self.wrangler.get_pip_path(project_name)
        
        # Check if PyInstaller is already installed
        try:
            result = subprocess.run(
                [str(pip_path), "show", "pyinstaller"],
                capture_output=True,
                text=True,
                timeout=30,
                **_subprocess_args()
            )
            
            if result.returncode == 0:
                return True, "PyInstaller is ready"
            
            # Not installed, install it
            result = subprocess.run(
                [str(pip_path), "install", "pyinstaller"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for install
                **_subprocess_args()
            )
            
            if result.returncode == 0:
                return True, "PyInstaller installed successfully"
            else:
                return False, f"Failed to install PyInstaller: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Timed out installing PyInstaller"
        except Exception as e:
            return False, f"Error checking PyInstaller: {e}"
    
    def _get_hidden_imports(self, packages: list[str]) -> list[str]:
        """Get hidden imports needed for the given packages."""
        hidden = []
        for pkg in packages:
            # Check both the package name and common aliases
            pkg_lower = pkg.lower()
            for known_pkg, imports in HIDDEN_IMPORTS.items():
                if known_pkg.lower() == pkg_lower:
                    hidden.extend(imports)
        return list(set(hidden))  # Remove duplicates
    
    def _get_datas(self, packages: list[str]) -> list[str]:
        """Get data file patterns needed for the given packages."""
        datas = []
        for pkg in packages:
            pkg_lower = pkg.lower()
            for known_pkg, pattern in DATAS_PATTERNS.items():
                if known_pkg.lower() == pkg_lower:
                    datas.append(pattern)
        return datas
    
    def build(
        self,
        project_path: Path,
        project_name: str,
        main_file: str = "main.py",
        app_name: Optional[str] = None,
        onefile: bool = True,
        windowed: bool = True,
        icon_path: Optional[Path] = None,
        packages: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[BuildProgress], None]] = None
    ) -> BuildResult:
        """
        Build an executable for the current platform.
        
        Args:
            project_path: Path to the project directory
            project_name: Name of the project (for venv lookup)
            main_file: Main Python file to build
            app_name: Name for the output executable (defaults to project_name)
            onefile: Bundle into single file (default True)
            windowed: Hide console window (default True, for GUI apps)
            icon_path: Path to icon file (.icns for Mac, .ico for Windows)
            packages: List of packages installed (for hidden imports detection)
            progress_callback: Callback for progress updates
            
        Returns:
            BuildResult with success status and output path
        """
        def report(stage: str, message: str, percent: int = 0):
            if progress_callback:
                progress_callback(BuildProgress(stage, message, percent))
        
        warnings = []
        app_name = app_name or project_name
        
        # Validate inputs
        main_path = project_path / main_file
        if not main_path.exists():
            return BuildResult(
                success=False,
                message=f"Main file not found: {main_file}",
                details=f"Expected at: {main_path}"
            )
        
        report('preparing', 'Checking build environment...', 5)
        
        # Ensure PyInstaller is available
        success, message = self._ensure_pyinstaller(project_name)
        if not success:
            return BuildResult(success=False, message=message)
        
        report('preparing', 'PyInstaller ready', 10)
        
        # Get paths
        python_path = self.wrangler.get_python_path(project_name)
        build_dir = self._get_build_dir(project_path)
        
        # Create build directory
        try:
            build_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return BuildResult(
                success=False,
                message="Couldn't create build directory",
                details=str(e)
            )
        
        # Build the PyInstaller command
        cmd = [
            str(python_path), "-m", "PyInstaller",
            "--clean",  # Clean cache before building
            "--noconfirm",  # Don't ask for confirmation
            f"--name={app_name}",
            f"--distpath={build_dir}",
            f"--workpath={project_path / 'build'}",  # Temp build files
            f"--specpath={project_path}",  # Where to put the .spec file
        ]
        
        if onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")
        
        if windowed:
            cmd.append("--windowed")
        else:
            cmd.append("--console")
        
        # Add icon if provided
        if icon_path and icon_path.exists():
            # Validate icon format for platform
            if self.system == "Darwin" and icon_path.suffix.lower() == ".icns":
                cmd.append(f"--icon={icon_path}")
            elif self.system == "Windows" and icon_path.suffix.lower() == ".ico":
                cmd.append(f"--icon={icon_path}")
            elif icon_path.suffix.lower() == ".png":
                # PyInstaller can use PNG directly on some platforms
                cmd.append(f"--icon={icon_path}")
                warnings.append("PNG icon used - .icns (Mac) or .ico (Windows) recommended")
            else:
                warnings.append(f"Icon format {icon_path.suffix} may not work on {self.get_platform_name()}")
        
        # Add hidden imports based on packages
        if packages:
            hidden_imports = self._get_hidden_imports(packages)
            for imp in hidden_imports:
                cmd.append(f"--hidden-import={imp}")
            
            # Add data files
            datas = self._get_datas(packages)
            for data in datas:
                cmd.append(f"--collect-data={data.split(':')[0]}")
            
            # Add --collect-all for packages that need full bundling
            # (whisper needs mel_filters.npz, tkinterdnd2 needs native libs, etc.)
            packages_lower = [p.lower() for p in packages]
            for collect_pkg in COLLECT_ALL_PACKAGES:
                if collect_pkg.lower() in packages_lower:
                    cmd.append(f"--collect-all={collect_pkg}")
        
        # Add the main file
        cmd.append(str(main_path))
        
        report('analyzing', 'Analyzing dependencies...', 20)
        
        # Run PyInstaller
        try:
            process = subprocess.Popen(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                **_subprocess_args()
            )
            
            output_lines = []
            current_percent = 20
            
            # Process output in real-time
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                    
                output_lines.append(line)
                line_lower = line.lower()
                
                # Update progress based on PyInstaller output
                if 'analyzing' in line_lower:
                    report('analyzing', 'Analyzing imports...', min(current_percent + 2, 40))
                    current_percent = min(current_percent + 2, 40)
                elif 'processing' in line_lower:
                    report('building', 'Processing modules...', min(current_percent + 1, 60))
                    current_percent = min(current_percent + 1, 60)
                elif 'building' in line_lower and 'exe' in line_lower:
                    report('building', 'Building executable...', 70)
                    current_percent = 70
                elif 'building' in line_lower and ('pkg' in line_lower or 'app' in line_lower):
                    report('packaging', 'Creating application bundle...', 85)
                    current_percent = 85
                elif 'completed successfully' in line_lower:
                    report('done', 'Build complete!', 100)
                elif 'warning' in line_lower:
                    # Capture warnings but don't stop
                    warnings.append(line.strip())
            
            process.wait(timeout=600)  # 10 minute timeout
            
            full_output = ''.join(output_lines)
            
            if process.returncode != 0:
                # Find the actual error
                error_lines = [l for l in output_lines if 'error' in l.lower()]
                error_msg = error_lines[-1] if error_lines else "Build failed"
                
                return BuildResult(
                    success=False,
                    message="Build failed",
                    details=full_output[-2000:],  # Last 2000 chars
                    warnings=warnings
                )
            
            # Find the output file
            if onefile:
                if self.system == "Darwin":
                    # On Mac, --onefile creates an .app bundle
                    output_path = build_dir / f"{app_name}.app"
                    if not output_path.exists():
                        # Sometimes it's just the executable
                        output_path = build_dir / app_name
                elif self.system == "Windows":
                    output_path = build_dir / f"{app_name}.exe"
                else:
                    output_path = build_dir / app_name
            else:
                output_path = build_dir / app_name
            
            if not output_path.exists():
                # Try to find what was actually created
                possible_outputs = list(build_dir.glob(f"{app_name}*"))
                if possible_outputs:
                    output_path = possible_outputs[0]
                else:
                    return BuildResult(
                        success=False,
                        message="Build completed but output not found",
                        details=f"Expected at: {output_path}\n\nBuild output:\n{full_output[-1000:]}",
                        warnings=warnings
                    )
            
            # Clean up build artifacts (optional)
            self._cleanup_build_artifacts(project_path, app_name)
            
            report('done', f'Build complete: {output_path.name}', 100)
            
            return BuildResult(
                success=True,
                message=f"Built successfully: {output_path.name}",
                output_path=output_path,
                details=f"Output: {output_path}",
                warnings=warnings
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            return BuildResult(
                success=False,
                message="Build timed out after 10 minutes",
                details="The build process took too long. Your project might be very large.",
                warnings=warnings
            )
        except Exception as e:
            return BuildResult(
                success=False,
                message=f"Build error: {e}",
                details=str(e),
                warnings=warnings
            )
    
    def _cleanup_build_artifacts(self, project_path: Path, app_name: str):
        """Clean up temporary build files."""
        try:
            # Remove build directory (PyInstaller work files)
            build_work = project_path / "build"
            if build_work.exists():
                shutil.rmtree(build_work)
            
            # Optionally remove .spec file (keep it for now, useful for debugging)
            # spec_file = project_path / f"{app_name}.spec"
            # if spec_file.exists():
            #     spec_file.unlink()
            
        except Exception:
            pass  # Cleanup failure is not critical
    
    def get_build_history(self, project_path: Path) -> list[dict]:
        """
        Get list of previous builds for a project.
        
        Returns list of dicts with:
        - name: filename
        - path: full path
        - size: size in bytes
        - modified: modification time
        """
        build_dir = self._get_build_dir(project_path)
        
        if not build_dir.exists():
            return []
        
        builds = []
        
        for item in build_dir.iterdir():
            if item.name.startswith('.'):
                continue
                
            try:
                stat = item.stat()
                builds.append({
                    'name': item.name,
                    'path': item,
                    'size': stat.st_size if item.is_file() else self._get_dir_size(item),
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
            except Exception:
                pass
        
        # Sort by modified time, newest first
        builds.sort(key=lambda b: b['modified'], reverse=True)
        
        return builds
    
    def _get_dir_size(self, path: Path) -> int:
        """Get total size of a directory."""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total
    
    def format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def open_build_folder(self, project_path: Path) -> bool:
        """Open the TPC Builds folder in the system file browser."""
        build_dir = self._get_build_dir(project_path)
        
        # Create folder if it doesn't exist - user just wants to see where builds go
        if not build_dir.exists():
            build_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.system == "Darwin":
                subprocess.run(["open", str(build_dir)], check=True)
            elif self.system == "Windows":
                subprocess.run(["explorer", str(build_dir)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(build_dir)], check=True)
            return True
        except Exception:
            return False


# === Quick test ===
if __name__ == "__main__":
    orchestrator = BuildOrchestrator()
    
    print("Build Orchestrator")
    print("=" * 40)
    print(f"Platform: {orchestrator.get_platform_name()}")
    print(f"Can build: {orchestrator.can_build_for_current_platform()}")
    print(f"Output extension: {orchestrator.get_output_extension() or '(none)'}")
    
    print("\nHidden imports for PyQt6:")
    for imp in HIDDEN_IMPORTS.get('PyQt6', []):
        print(f"  - {imp}")

"""
Environment Wrangler for TPC.

Manages hidden virtual environments for project builds.
Users never see these - they just click "Build" and it works.

Venvs are stored at ~/.tpc/venvs/ProjectName/ to keep them
out of the project folder and avoid confusing version control.
"""

import subprocess
import sys
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
import shutil


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


# Where we hide our venvs
TPC_VENVS_DIR = Path.home() / ".tpc" / "venvs"

# Python versions known to work well with PyInstaller
# Ordered by preference (most stable for packaging first)
PREFERRED_PYTHON_VERSIONS = ['3.12', '3.11', '3.10']

# Versions that might have issues (warn user)
BLEEDING_EDGE_VERSIONS = ['3.13', '3.14', '3.15']

# Packages that can fail to install without blocking the build
# These often have platform-specific issues or require system dependencies
OPTIONAL_PACKAGES = {
    'tkinterdnd2',      # Drag-and-drop - needs tcl/tk dev headers
    'pyobjc',           # macOS only
    'pyobjc-core',      # macOS only  
    'pyobjc-framework-cocoa',  # macOS only
    'pywin32',          # Windows only
    'pywinpty',         # Windows only
    'pynput',           # Can have permission issues
    'keyboard',         # Can have permission issues
}


def find_best_python() -> tuple[str, str, list[str]]:
    """
    Find the best available Python for creating venvs.
    
    Prefers stable versions known to work well with PyInstaller.
    
    Returns:
        (python_path, version_string, warnings)
        e.g., ('/opt/homebrew/bin/python3.12', '3.12.1', [])
    """
    warnings = []
    found_pythons = []
    
    # Check Homebrew locations (macOS)
    if platform.system() == "Darwin":
        for version in PREFERRED_PYTHON_VERSIONS:
            brew_path = Path(f'/opt/homebrew/bin/python{version}')
            if brew_path.exists():
                actual_version = _get_python_version(str(brew_path))
                if actual_version:
                    found_pythons.append((str(brew_path), actual_version, 'homebrew'))
            
            # Also check /usr/local for Intel Macs
            intel_path = Path(f'/usr/local/bin/python{version}')
            if intel_path.exists():
                actual_version = _get_python_version(str(intel_path))
                if actual_version:
                    found_pythons.append((str(intel_path), actual_version, 'homebrew-intel'))
    
    # Check Windows locations
    elif platform.system() == "Windows":
        for version in PREFERRED_PYTHON_VERSIONS:
            # Check if py launcher knows about this version
            try:
                result = subprocess.run(
                    ['py', f'-{version}', '--version'],
                    capture_output=True, text=True, timeout=5,
                    **_subprocess_args()
                )
                if result.returncode == 0:
                    actual_version = result.stdout.strip().replace('Python ', '')
                    # Get the ACTUAL executable path from py launcher
                    path_result = subprocess.run(
                        ['py', f'-{version}', '-c', 'import sys; print(sys.executable)'],
                        capture_output=True, text=True, timeout=5,
                        **_subprocess_args()
                    )
                    if path_result.returncode == 0:
                        actual_path = path_result.stdout.strip()
                        found_pythons.append((actual_path, actual_version, 'py-launcher'))
            except:
                pass
            
            # Check AppData location
            appdata = Path.home() / 'AppData' / 'Local' / 'Programs' / 'Python'
            for python_dir in appdata.glob(f'Python{version.replace(".", "")}*'):
                python_exe = python_dir / 'python.exe'
                if python_exe.exists():
                    actual_version = _get_python_version(str(python_exe))
                    if actual_version:
                        found_pythons.append((str(python_exe), actual_version, 'appdata'))
            
            # Also check common install location C:\PythonXX
            direct_path = Path(f'C:/Python{version.replace(".", "")}/python.exe')
            if direct_path.exists():
                actual_version = _get_python_version(str(direct_path))
                if actual_version:
                    found_pythons.append((str(direct_path), actual_version, 'direct'))
    
    # Check generic python3 and versioned commands (Linux/Unix/fallback)
    for version in PREFERRED_PYTHON_VERSIONS:
        for cmd in [f'python{version}', f'python{version.replace(".", "")}']:
            python_path = shutil.which(cmd)
            if python_path:
                actual_version = _get_python_version(python_path)
                if actual_version:
                    found_pythons.append((python_path, actual_version, 'path'))
    
    # If we found a preferred version, use the first one
    if found_pythons:
        best = found_pythons[0]
        return (best[0], best[1], warnings)
    
    # Fall back to sys.executable (whatever's running TPC)
    current_python = sys.executable
    current_version = _get_python_version(current_python) or f'{sys.version_info.major}.{sys.version_info.minor}'
    
    # Check if current Python is bleeding edge
    for edge_version in BLEEDING_EDGE_VERSIONS:
        if current_version.startswith(edge_version):
            warnings.append(
                f"Python {current_version} is very new and may have packaging issues. "
                f"Consider installing Python 3.12 for best results."
            )
            break
    
    return (current_python, current_version, warnings)


def _get_python_version(python_path: str) -> Optional[str]:
    """Get the version string from a Python executable."""
    try:
        result = subprocess.run(
            [python_path, '--version'],
            capture_output=True, text=True, timeout=5,
            **_subprocess_args()
        )
        if result.returncode == 0:
            # Output is like "Python 3.12.1"
            return result.stdout.strip().replace('Python ', '')
    except:
        pass
    return None


def get_available_pythons() -> list[dict]:
    """
    Get list of all available Python installations.
    
    Returns list of dicts with 'path', 'version', 'source', 'recommended'
    Useful for future Settings UI.
    """
    pythons = []
    seen_paths = set()
    
    # Check all potential locations
    search_locations = []
    
    if platform.system() == "Darwin":
        # Homebrew ARM
        search_locations.extend([
            Path(f'/opt/homebrew/bin/python{v}') for v in ['3.13', '3.12', '3.11', '3.10', '3.9']
        ])
        # Homebrew Intel
        search_locations.extend([
            Path(f'/usr/local/bin/python{v}') for v in ['3.13', '3.12', '3.11', '3.10', '3.9']
        ])
    
    # Generic path search
    for version in ['3.13', '3.12', '3.11', '3.10', '3.9']:
        which_result = shutil.which(f'python{version}')
        if which_result:
            search_locations.append(Path(which_result))
    
    # Check each location
    for loc in search_locations:
        if loc.exists() and str(loc) not in seen_paths:
            version = _get_python_version(str(loc))
            if version:
                seen_paths.add(str(loc))
                pythons.append({
                    'path': str(loc),
                    'version': version,
                    'recommended': any(version.startswith(v) for v in PREFERRED_PYTHON_VERSIONS)
                })
    
    return pythons


@dataclass
class VenvResult:
    """Result of a venv operation."""
    success: bool
    message: str
    details: str = ""  # Detailed output for debugging


@dataclass
class InstallProgress:
    """Progress update during package installation."""
    package: str
    index: int
    total: int
    status: str  # 'installing', 'done', 'failed'
    message: str = ""


class EnvironmentWrangler:
    """
    Manages virtual environments for TPC projects.
    
    Usage:
        wrangler = EnvironmentWrangler()
        
        # Create a venv for a project
        result = wrangler.create_venv("MyProject")
        
        # Install packages
        result = wrangler.install_packages("MyProject", ["PyQt6", "requests"])
        
        # Get the Python executable for the venv
        python = wrangler.get_python_path("MyProject")
    """
    
    def __init__(self):
        self.venvs_dir = TPC_VENVS_DIR
    
    def _get_venv_path(self, project_name: str) -> Path:
        """Get the path to a project's venv directory."""
        # Sanitize project name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in project_name)
        safe_name = safe_name.strip()
        return self.venvs_dir / safe_name
    
    def get_python_path(self, project_name: str) -> Path:
        """Get the path to the Python executable in a project's venv."""
        venv_path = self._get_venv_path(project_name)
        
        if platform.system() == "Windows":
            return venv_path / "Scripts" / "python.exe"
        else:
            return venv_path / "bin" / "python"
    
    def get_pip_path(self, project_name: str) -> Path:
        """Get the path to pip in a project's venv."""
        venv_path = self._get_venv_path(project_name)
        
        if platform.system() == "Windows":
            return venv_path / "Scripts" / "pip.exe"
        else:
            return venv_path / "bin" / "pip"
    
    def venv_exists(self, project_name: str) -> bool:
        """Check if a venv exists for this project."""
        python_path = self.get_python_path(project_name)
        return python_path.exists()
    
    def create_venv(self, project_name: str, force: bool = False) -> VenvResult:
        """
        Create a virtual environment for a project.
        
        Args:
            project_name: Name of the project
            force: If True, delete existing venv and create fresh
            
        Returns:
            VenvResult with success status and message
        """
        venv_path = self._get_venv_path(project_name)
        
        # Handle existing venv
        if venv_path.exists():
            if force:
                try:
                    shutil.rmtree(venv_path)
                except Exception as e:
                    return VenvResult(
                        success=False,
                        message="Couldn't remove existing environment",
                        details=str(e)
                    )
            else:
                # Check if it's actually valid
                if self.venv_exists(project_name):
                    return VenvResult(
                        success=True,
                        message="Environment already exists",
                        details=str(venv_path)
                    )
                else:
                    # Corrupted venv, remove and recreate
                    try:
                        shutil.rmtree(venv_path)
                    except Exception as e:
                        return VenvResult(
                            success=False,
                            message="Couldn't clean up corrupted environment",
                            details=str(e)
                        )
        
        # Create parent directory if needed
        try:
            self.venvs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return VenvResult(
                success=False,
                message="Couldn't create venvs directory",
                details=str(e)
            )
        
        # Create the venv
        try:
            # Find the best Python for packaging (prefers stable versions)
            python_exe, python_version, version_warnings = find_best_python()
            
            result = subprocess.run(
                [python_exe, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                **_subprocess_args()
            )
            
            if result.returncode != 0:
                return VenvResult(
                    success=False,
                    message="Failed to create environment",
                    details=result.stderr or result.stdout
                )
            
            # Verify it worked
            if not self.venv_exists(project_name):
                return VenvResult(
                    success=False,
                    message="Environment created but Python not found",
                    details=f"Expected at: {self.get_python_path(project_name)}"
                )
            
            # Upgrade pip to avoid warnings
            pip_path = self.get_pip_path(project_name)
            subprocess.run(
                [str(pip_path), "install", "--upgrade", "pip"],
                capture_output=True,
                timeout=60,
                **_subprocess_args()
            )
            
            # Build details message
            details = f"Created with Python {python_version}\nLocation: {venv_path}"
            if version_warnings:
                details += "\n\n⚠️ " + "\n⚠️ ".join(version_warnings)
            
            return VenvResult(
                success=True,
                message=f"Environment created (Python {python_version})",
                details=details
            )
            
        except subprocess.TimeoutExpired:
            return VenvResult(
                success=False,
                message="Timed out creating environment",
                details="This might be a system issue - try again?"
            )
        except Exception as e:
            return VenvResult(
                success=False,
                message="Error creating environment",
                details=str(e)
            )
    
    def install_packages(
        self, 
        project_name: str, 
        packages: list[str],
        progress_callback: Optional[Callable[[InstallProgress], None]] = None
    ) -> VenvResult:
        """
        Install packages into a project's venv.
        
        Args:
            project_name: Name of the project
            packages: List of package names to install
            progress_callback: Optional callback for progress updates
            
        Returns:
            VenvResult with success status and message
        """
        if not packages:
            return VenvResult(
                success=True,
                message="No packages to install",
                details=""
            )
        
        # Make sure venv exists
        if not self.venv_exists(project_name):
            result = self.create_venv(project_name)
            if not result.success:
                return result
        
        pip_path = self.get_pip_path(project_name)
        
        if not pip_path.exists():
            return VenvResult(
                success=False,
                message="pip not found in environment",
                details=f"Expected at: {pip_path}"
            )
        
        # Install all packages at once (faster than one by one)
        # But we'll report progress for UX
        total = len(packages)
        failed_packages = []
        installed_packages = []
        
        for i, package in enumerate(packages):
            if progress_callback:
                progress_callback(InstallProgress(
                    package=package,
                    index=i + 1,
                    total=total,
                    status='installing',
                    message=f"Installing {package}..."
                ))
            
            try:
                result = subprocess.run(
                    [str(pip_path), "install", package],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout per package
                    **_subprocess_args()
                )
                
                if result.returncode == 0:
                    installed_packages.append(package)
                    if progress_callback:
                        progress_callback(InstallProgress(
                            package=package,
                            index=i + 1,
                            total=total,
                            status='done',
                            message=f"Installed {package}"
                        ))
                else:
                    failed_packages.append((package, result.stderr))
                    if progress_callback:
                        progress_callback(InstallProgress(
                            package=package,
                            index=i + 1,
                            total=total,
                            status='failed',
                            message=f"Failed to install {package}"
                        ))
                        
            except subprocess.TimeoutExpired:
                failed_packages.append((package, "Installation timed out"))
                if progress_callback:
                    progress_callback(InstallProgress(
                        package=package,
                        index=i + 1,
                        total=total,
                        status='failed',
                        message=f"Timed out installing {package}"
                    ))
            except Exception as e:
                failed_packages.append((package, str(e)))
                if progress_callback:
                    progress_callback(InstallProgress(
                        package=package,
                        index=i + 1,
                        total=total,
                        status='failed',
                        message=f"Error installing {package}: {e}"
                    ))
        
        # Build result
        # Separate required failures from optional package failures
        required_failures = [(p, e) for p, e in failed_packages if p.lower() not in OPTIONAL_PACKAGES]
        optional_failures = [(p, e) for p, e in failed_packages if p.lower() in OPTIONAL_PACKAGES]
        
        if not failed_packages:
            return VenvResult(
                success=True,
                message=f"Installed {len(installed_packages)} package(s)",
                details=", ".join(installed_packages)
            )
        elif not required_failures:
            # Only optional packages failed - that's OK
            optional_names = [p[0] for p in optional_failures]
            details = f"Installed: {', '.join(installed_packages)}"
            details += f"\n\n⚠️ Optional packages skipped (platform-specific): {', '.join(optional_names)}"
            return VenvResult(
                success=True,  # Still success!
                message=f"Installed {len(installed_packages)} package(s) ({len(optional_failures)} optional skipped)",
                details=details
            )
        elif installed_packages:
            failed_names = [p[0] for p in required_failures]
            return VenvResult(
                success=False,
                message=f"Installed {len(installed_packages)}, failed {len(required_failures)}",
                details=f"Failed: {', '.join(failed_names)}"
            )
        else:
            return VenvResult(
                success=False,
                message="All package installations failed",
                details="\n".join(f"{p}: {e}" for p, e in failed_packages)
            )
    
    def install_from_requirements(
        self,
        project_name: str,
        requirements_path: Path,
        progress_callback: Optional[Callable[[InstallProgress], None]] = None
    ) -> VenvResult:
        """
        Install packages from a requirements.txt file.
        
        Args:
            project_name: Name of the project
            requirements_path: Path to requirements.txt
            progress_callback: Optional callback for progress updates
            
        Returns:
            VenvResult with success status and message
        """
        if not requirements_path.exists():
            return VenvResult(
                success=False,
                message="requirements.txt not found",
                details=str(requirements_path)
            )
        
        # Make sure venv exists
        if not self.venv_exists(project_name):
            result = self.create_venv(project_name)
            if not result.success:
                return result
        
        pip_path = self.get_pip_path(project_name)
        
        if progress_callback:
            progress_callback(InstallProgress(
                package="requirements.txt",
                index=1,
                total=1,
                status='installing',
                message="Installing from requirements.txt..."
            ))
        
        try:
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_path)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for all packages
                **_subprocess_args()
            )
            
            if result.returncode == 0:
                # Count installed packages from output
                lines = result.stdout.split('\n')
                installed = [l for l in lines if 'Successfully installed' in l]
                
                if progress_callback:
                    progress_callback(InstallProgress(
                        package="requirements.txt",
                        index=1,
                        total=1,
                        status='done',
                        message="All packages installed"
                    ))
                
                return VenvResult(
                    success=True,
                    message="Installed all packages from requirements.txt",
                    details=result.stdout
                )
            else:
                if progress_callback:
                    progress_callback(InstallProgress(
                        package="requirements.txt",
                        index=1,
                        total=1,
                        status='failed',
                        message="Installation failed"
                    ))
                
                return VenvResult(
                    success=False,
                    message="Failed to install from requirements.txt",
                    details=result.stderr or result.stdout
                )
                
        except subprocess.TimeoutExpired:
            return VenvResult(
                success=False,
                message="Installation timed out",
                details="Try installing fewer packages at once"
            )
        except Exception as e:
            return VenvResult(
                success=False,
                message="Error during installation",
                details=str(e)
            )
    
    def verify_imports(
        self,
        project_name: str,
        modules: list[str]
    ) -> VenvResult:
        """
        Verify that modules can be imported in the venv.
        
        Args:
            project_name: Name of the project
            modules: List of module names to try importing
            
        Returns:
            VenvResult with success status and which imports worked/failed
        """
        if not self.venv_exists(project_name):
            return VenvResult(
                success=False,
                message="No environment exists for this project",
                details=""
            )
        
        python_path = self.get_python_path(project_name)
        
        working = []
        broken = []
        
        for module in modules:
            try:
                result = subprocess.run(
                    [str(python_path), "-c", f"import {module}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    **_subprocess_args()
                )
                
                if result.returncode == 0:
                    working.append(module)
                else:
                    broken.append(module)
                    
            except Exception:
                broken.append(module)
        
        if not broken:
            return VenvResult(
                success=True,
                message=f"All {len(working)} imports verified",
                details=", ".join(working)
            )
        elif working:
            return VenvResult(
                success=False,
                message=f"{len(working)} working, {len(broken)} failed",
                details=f"Failed: {', '.join(broken)}"
            )
        else:
            return VenvResult(
                success=False,
                message="All imports failed",
                details=", ".join(broken)
            )
    
    def delete_venv(self, project_name: str) -> VenvResult:
        """
        Delete a project's virtual environment.
        
        Args:
            project_name: Name of the project
            
        Returns:
            VenvResult with success status
        """
        venv_path = self._get_venv_path(project_name)
        
        if not venv_path.exists():
            return VenvResult(
                success=True,
                message="No environment to delete",
                details=""
            )
        
        try:
            shutil.rmtree(venv_path)
            return VenvResult(
                success=True,
                message="Environment deleted",
                details=str(venv_path)
            )
        except Exception as e:
            return VenvResult(
                success=False,
                message="Couldn't delete environment",
                details=str(e)
            )
    
    def get_installed_packages(self, project_name: str) -> list[str]:
        """
        Get list of packages installed in the venv.
        
        Returns empty list if venv doesn't exist or on error.
        """
        if not self.venv_exists(project_name):
            return []
        
        pip_path = self.get_pip_path(project_name)
        
        try:
            result = subprocess.run(
                [str(pip_path), "freeze"],
                capture_output=True,
                text=True,
                timeout=30,
                **_subprocess_args()
            )
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.strip().split('\n'):
                    if line and '==' in line:
                        pkg_name = line.split('==')[0]
                        packages.append(pkg_name)
                return packages
            return []
            
        except Exception:
            return []
    
    def get_venv_size(self, project_name: str) -> Optional[int]:
        """
        Get the size of a project's venv in bytes.
        
        Returns None if venv doesn't exist.
        """
        venv_path = self._get_venv_path(project_name)
        
        if not venv_path.exists():
            return None
        
        total = 0
        try:
            for path in venv_path.rglob('*'):
                if path.is_file():
                    total += path.stat().st_size
            return total
        except Exception:
            return None
    
    def format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# === Quick test ===
if __name__ == "__main__":
    wrangler = EnvironmentWrangler()
    
    print(f"Venvs directory: {wrangler.venvs_dir}")
    print()
    
    # Test with a dummy project
    test_project = "TPC_Test_Project"
    
    print(f"Creating venv for '{test_project}'...")
    result = wrangler.create_venv(test_project)
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")
    if result.details:
        print(f"  Details: {result.details}")
    
    if result.success:
        print()
        print("Installing test package (requests)...")
        
        def show_progress(p: InstallProgress):
            print(f"  [{p.index}/{p.total}] {p.status}: {p.message}")
        
        result = wrangler.install_packages(test_project, ["requests"], show_progress)
        print(f"  Success: {result.success}")
        print(f"  Message: {result.message}")
        
        print()
        print("Verifying import...")
        result = wrangler.verify_imports(test_project, ["requests"])
        print(f"  Success: {result.success}")
        print(f"  Message: {result.message}")
        
        print()
        size = wrangler.get_venv_size(test_project)
        if size:
            print(f"Venv size: {wrangler.format_size(size)}")
        
        print()
        print("Cleaning up...")
        result = wrangler.delete_venv(test_project)
        print(f"  {result.message}")

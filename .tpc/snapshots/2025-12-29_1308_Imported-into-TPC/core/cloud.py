"""
Cloud folder detection for TPC 2.0.

Detects common cloud storage services (iCloud, Dropbox, OneDrive, Google Drive)
and helps users pick where to store their projects.

The goal: your projects live in a cloud folder, sync happens automatically,
TPC doesn't have to think about it.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class CloudFolder:
    """A detected cloud storage folder."""
    
    service: str          # "iCloud Drive", "Dropbox", "OneDrive", "Google Drive", "Local"
    path: Path            # Actual filesystem path
    display_path: str     # Friendly path for UI
    available: bool       # Does the folder exist and is accessible?
    
    def __str__(self) -> str:
        return f"{self.service}: {self.display_path}"
    
    def tpc_projects_path(self) -> Path:
        """Return the path where TPC Projects folder would live."""
        return self.path / "TPC Projects"


def _check_path(path: Path) -> bool:
    """Check if a path exists and is accessible."""
    try:
        return path.exists() and path.is_dir()
    except (PermissionError, OSError):
        return False


def _get_mac_cloud_folders() -> list[CloudFolder]:
    """Detect cloud folders on macOS."""
    folders = []
    home = Path.home()
    
    # iCloud Drive
    # The actual path is ugly, but it's where iCloud lives
    icloud_path = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    folders.append(CloudFolder(
        service="iCloud Drive",
        path=icloud_path,
        display_path="iCloud Drive",
        available=_check_path(icloud_path)
    ))
    
    # Dropbox - simple path
    dropbox_path = home / "Dropbox"
    folders.append(CloudFolder(
        service="Dropbox",
        path=dropbox_path,
        display_path="Dropbox",
        available=_check_path(dropbox_path)
    ))
    
    # OneDrive - lives in CloudStorage on Mac
    # Could be "OneDrive" or "OneDrive - Personal" or "OneDrive - CompanyName"
    cloud_storage = home / "Library" / "CloudStorage"
    onedrive_found = False
    if cloud_storage.exists():
        try:
            for item in cloud_storage.iterdir():
                if item.name.startswith("OneDrive") and item.is_dir():
                    # Clean up the display name
                    display_name = item.name.replace("OneDrive-Personal", "OneDrive")
                    if display_name.startswith("OneDrive-"):
                        display_name = "OneDrive"
                    folders.append(CloudFolder(
                        service="OneDrive",
                        path=item,
                        display_path=display_name,
                        available=True
                    ))
                    onedrive_found = True
                    break  # Just take the first one
        except PermissionError:
            pass
    
    if not onedrive_found:
        # Add placeholder so UI can show it as unavailable
        folders.append(CloudFolder(
            service="OneDrive",
            path=home / "OneDrive",
            display_path="OneDrive",
            available=False
        ))
    
    # Google Drive - also in CloudStorage on Mac
    gdrive_found = False
    if cloud_storage.exists():
        try:
            for item in cloud_storage.iterdir():
                if item.name.startswith("GoogleDrive") and item.is_dir():
                    folders.append(CloudFolder(
                        service="Google Drive",
                        path=item,
                        display_path="Google Drive",
                        available=True
                    ))
                    gdrive_found = True
                    break
        except PermissionError:
            pass
    
    if not gdrive_found:
        folders.append(CloudFolder(
            service="Google Drive",
            path=home / "Google Drive",
            display_path="Google Drive",
            available=False
        ))
    
    return folders


def _get_windows_cloud_folders() -> list[CloudFolder]:
    """Detect cloud folders on Windows."""
    folders = []
    home = Path.home()
    
    # iCloud Drive on Windows
    icloud_path = home / "iCloudDrive"
    folders.append(CloudFolder(
        service="iCloud Drive",
        path=icloud_path,
        display_path="iCloud Drive",
        available=_check_path(icloud_path)
    ))
    
    # Dropbox - usually in user profile
    dropbox_path = home / "Dropbox"
    folders.append(CloudFolder(
        service="Dropbox",
        path=dropbox_path,
        display_path="Dropbox",
        available=_check_path(dropbox_path)
    ))
    
    # OneDrive - check environment variable first, then common location
    onedrive_env = os.environ.get("OneDrive", "")
    if onedrive_env and _check_path(Path(onedrive_env)):
        folders.append(CloudFolder(
            service="OneDrive",
            path=Path(onedrive_env),
            display_path="OneDrive",
            available=True
        ))
    else:
        onedrive_path = home / "OneDrive"
        folders.append(CloudFolder(
            service="OneDrive",
            path=onedrive_path,
            display_path="OneDrive",
            available=_check_path(onedrive_path)
        ))
    
    # Google Drive - check common locations
    gdrive_path = home / "Google Drive"
    gdrive_alt = home / "My Drive"
    
    if _check_path(gdrive_path):
        folders.append(CloudFolder(
            service="Google Drive",
            path=gdrive_path,
            display_path="Google Drive",
            available=True
        ))
    elif _check_path(gdrive_alt):
        folders.append(CloudFolder(
            service="Google Drive",
            path=gdrive_alt,
            display_path="Google Drive",
            available=True
        ))
    else:
        folders.append(CloudFolder(
            service="Google Drive",
            path=gdrive_path,
            display_path="Google Drive",
            available=False
        ))
    
    return folders


def detect_cloud_folders() -> list[CloudFolder]:
    """
    Detect available cloud storage folders on this system.
    
    Returns list of CloudFolder objects, sorted with available folders first,
    then by service name.
    """
    if sys.platform == "darwin":
        folders = _get_mac_cloud_folders()
    elif sys.platform == "win32":
        folders = _get_windows_cloud_folders()
    else:
        # Linux - just check common paths
        folders = []
        home = Path.home()
        
        for service, path in [
            ("Dropbox", home / "Dropbox"),
            ("OneDrive", home / "OneDrive"),
            ("Google Drive", home / "Google Drive"),
        ]:
            folders.append(CloudFolder(
                service=service,
                path=path,
                display_path=service,
                available=_check_path(path)
            ))
    
    # Sort: available first, then alphabetically
    folders.sort(key=lambda f: (not f.available, f.service))
    
    return folders


def get_available_cloud_folders() -> list[CloudFolder]:
    """Get only the cloud folders that are actually available."""
    return [f for f in detect_cloud_folders() if f.available]


def get_local_folder() -> CloudFolder:
    """Get the default local (non-cloud) folder option."""
    return CloudFolder(
        service="Local",
        path=Path.home() / "Documents",
        display_path="Documents (local only)",
        available=True
    )


def get_default_projects_location() -> Path:
    """
    Get the best default location for TPC Projects.
    
    Priority:
    1. First available cloud folder
    2. ~/Documents if no cloud folders
    
    Returns the full path including "TPC Projects" subfolder.
    """
    available = get_available_cloud_folders()
    
    if available:
        return available[0].tpc_projects_path()
    else:
        return Path.home() / "Documents" / "TPC Projects"


def ensure_projects_folder(base_path: Path) -> tuple[bool, str]:
    """
    Ensure the TPC Projects folder exists at the given location.
    
    Args:
        base_path: The cloud/local folder (e.g., ~/Dropbox)
    
    Returns:
        (success, message)
    """
    projects_path = base_path / "TPC Projects"
    
    try:
        projects_path.mkdir(parents=True, exist_ok=True)
        return True, f"Projects folder ready at {projects_path}"
    except PermissionError:
        return False, f"Permission denied creating {projects_path}"
    except OSError as e:
        return False, f"Could not create folder: {e}"


def identify_cloud_service(path: Path) -> Optional[str]:
    """
    Try to identify which cloud service a path belongs to.
    
    Useful for showing "✓ Synced via Dropbox" in the UI.
    
    Returns service name or None if not a recognized cloud folder.
    """
    path_str = str(path).lower()
    
    # Check for common indicators in the path
    if "dropbox" in path_str:
        return "Dropbox"
    elif "icloud" in path_str or "mobile documents" in path_str:
        return "iCloud Drive"
    elif "onedrive" in path_str:
        return "OneDrive"
    elif "google" in path_str and "drive" in path_str:
        return "Google Drive"
    
    # Check if path is under a known cloud folder
    for folder in detect_cloud_folders():
        if folder.available:
            try:
                path.relative_to(folder.path)
                return folder.service
            except ValueError:
                continue
    
    return None


# Quick test when run directly
if __name__ == "__main__":
    print("Detecting cloud folders...\n")
    
    for folder in detect_cloud_folders():
        status = "✓" if folder.available else "✗"
        print(f"{status} {folder.service}")
        print(f"  Path: {folder.path}")
        print(f"  Display: {folder.display_path}")
        print()
    
    print(f"\nDefault location: {get_default_projects_location()}")

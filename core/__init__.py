"""TPC core functionality."""

import sys

__version__ = "2.1.0"


def subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running git/python commands from a frozen PyInstaller executable.
    
    Usage:
        subprocess.run(["git", "status"], **subprocess_args())
    """
    kwargs = {}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = 0x08000000
    return kwargs


from .project import (
    Project, 
    find_tpc_projects, 
    DEFAULT_PROJECTS_ROOT,
    migrate_global_config,
    migrate_project_config,
    remove_from_tpc,
    get_config_dir,
    cleanup_stale_projects,
    get_orphan_folders,
)
from .config import (
    TPCConfig,
    get_config,
    save_config,
    is_first_run,
    complete_first_run,
    get_projects_root,
    update_projects_location,
)
from .cloud import (
    CloudFolder,
    detect_cloud_folders,
    get_available_cloud_folders,
    get_local_folder,
    get_default_projects_location,
    ensure_projects_folder,
    identify_cloud_service,
)
from .deps import (
    DependencyDetective, 
    ScanResult, 
    generate_requirements,
    compare_requirements,
    RequirementsComparison,
)
from .venv import (
    EnvironmentWrangler,
    VenvResult,
    InstallProgress,
    TPC_VENVS_DIR,
)
from .icons import (
    IconAlchemist,
    IconResult,
    ImageInfo,
)
from .build import (
    BuildOrchestrator,
    BuildResult,
    BuildProgress,
)
from .github import (
    has_github_credentials,
    get_github_token,
    get_github_username,
    save_github_credentials,
    clear_github_credentials,
    validate_token,
    clone_repository,
    fetch_user_repos,
)

__all__ = [
    "subprocess_args",
    # Project management
    "Project", 
    "find_tpc_projects", 
    "DEFAULT_PROJECTS_ROOT",
    "migrate_global_config",
    "migrate_project_config",
    "remove_from_tpc",
    "get_config_dir",
    "cleanup_stale_projects",
    "get_orphan_folders",
    # Config (TPC 2.0)
    "TPCConfig",
    "get_config",
    "save_config",
    "is_first_run",
    "complete_first_run",
    "get_projects_root",
    "update_projects_location",
    # Cloud detection (TPC 2.0)
    "CloudFolder",
    "detect_cloud_folders",
    "get_available_cloud_folders",
    "get_local_folder",
    "get_default_projects_location",
    "ensure_projects_folder",
    "identify_cloud_service",
    # Dependencies
    "DependencyDetective",
    "ScanResult", 
    "generate_requirements",
    "compare_requirements",
    "RequirementsComparison",
    # Virtual environments
    "EnvironmentWrangler",
    "VenvResult",
    "InstallProgress",
    "TPC_VENVS_DIR",
    # Icons
    "IconAlchemist",
    "IconResult",
    "ImageInfo",
    # Build
    "BuildOrchestrator",
    "BuildResult",
    "BuildProgress",
    # GitHub
    "has_github_credentials",
    "get_github_token",
    "get_github_username",
    "save_github_credentials",
    "clear_github_credentials",
    "validate_token",
    "clone_repository",
    "fetch_user_repos",
]

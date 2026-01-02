"""TPC core functionality - v3.5 with simple snapshot versioning."""

import sys

__version__ = "3.5.0"


def subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    return kwargs


# Project management
from .project_v3 import (
    Project,
    find_tpc_projects,
    invalidate_project_cache,
    DEFAULT_PROJECTS_ROOT,
    remove_from_tpc,
    get_config_dir,
    cleanup_stale_projects,
    get_orphan_folders,
    register_project_path,
    unregister_project_path,
    get_known_project_paths,
)

# Snapshot versioning (new in v3)
from .snapshots import (
    SnapshotManager,
    Snapshot,
    SnapshotResult,
    create_project_snapshot,
    list_project_snapshots,
    restore_project_snapshot,
    DEFAULT_IGNORE_PATTERNS,
)

# Dependency scanning
from .deps import (
    DependencyDetective, 
    ScanResult, 
    generate_requirements,
    compare_requirements,
    RequirementsComparison,
)

# Virtual environment management
from .venv import (
    EnvironmentWrangler,
    VenvResult,
    InstallProgress,
    TPC_VENVS_DIR,
)

# Icon conversion
from .icons import (
    IconAlchemist,
    IconResult,
    ImageInfo,
)

# Build/packaging
from .build import (
    BuildOrchestrator,
    BuildResult,
    BuildProgress,
)

# GitHub integration (simplified for backup only)
from .github import (
    has_github_credentials,
    get_github_token,
    get_github_username,
    save_github_credentials,
    clear_github_credentials,
    validate_token,
    clone_repository,
    fetch_user_repos,
    is_keyring_available,
)

# Backup to GitHub (one-way push)
from .backup import (
    backup_to_github,
    BackupResult,
    is_git_installed,
    has_git_repo,
    get_backup_status,
)

# Secrets detection
from .secrets import (
    scan_for_secrets,
    SecretFinding,
    get_severity_emoji,
    format_findings_for_display,
)

__all__ = [
    # Version
    "__version__",
    "subprocess_args",

    # Project
    "Project",
    "find_tpc_projects",
    "invalidate_project_cache",
    "DEFAULT_PROJECTS_ROOT",
    "remove_from_tpc",
    "get_config_dir",
    "cleanup_stale_projects",
    "get_orphan_folders",
    "register_project_path",
    "unregister_project_path",
    "get_known_project_paths",
    
    # Snapshots
    "SnapshotManager",
    "Snapshot",
    "SnapshotResult",
    "create_project_snapshot",
    "list_project_snapshots",
    "restore_project_snapshot",
    "DEFAULT_IGNORE_PATTERNS",
    
    # Dependencies
    "DependencyDetective",
    "ScanResult", 
    "generate_requirements",
    "compare_requirements",
    "RequirementsComparison",
    
    # Venv
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
    "is_keyring_available",
    
    # Backup
    "backup_to_github",
    "BackupResult",
    "is_git_installed",
    "has_git_repo",
    "get_backup_status",
    
    # Secrets
    "scan_for_secrets",
    "SecretFinding",
    "get_severity_emoji",
    "format_findings_for_display",
]

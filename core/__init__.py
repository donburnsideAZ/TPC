"""TPC core functionality."""

__version__ = "0.96"

from .project import Project, find_ptc_projects, DEFAULT_PROJECTS_ROOT
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
)

__all__ = [
    "Project", 
    "find_ptc_projects", 
    "DEFAULT_PROJECTS_ROOT",
    "DependencyDetective",
    "ScanResult", 
    "generate_requirements",
    "compare_requirements",
    "RequirementsComparison",
    "EnvironmentWrangler",
    "VenvResult",
    "InstallProgress",
    "TPC_VENVS_DIR",
    "IconAlchemist",
    "IconResult",
    "ImageInfo",
    "BuildOrchestrator",
    "BuildResult",
    "BuildProgress",
    "has_github_credentials",
    "get_github_token",
    "get_github_username",
    "save_github_credentials",
    "clear_github_credentials",
    "validate_token",
    "clone_repository",
]

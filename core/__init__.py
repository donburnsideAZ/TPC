"""TPC core functionality."""

__version__ = "0.86"

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
]

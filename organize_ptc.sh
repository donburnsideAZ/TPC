#!/bin/bash
# Run this from your PTC folder to organize the files

echo "Organizing PTC files..."

# Create the directory structure
mkdir -p ui/wizards
mkdir -p core
mkdir -p resources

# Move files to their proper locations
mv project.py core/
mv main_window.py ui/
mv workspace.py ui/
mv new_project.py ui/wizards/
mv adopt_project.py ui/wizards/

# Create the __init__.py files
cat > core/__init__.py << 'EOF'
"""PTC core functionality."""

from .project import Project, find_ptc_projects, DEFAULT_PROJECTS_ROOT

__all__ = ["Project", "find_ptc_projects", "DEFAULT_PROJECTS_ROOT"]
EOF

cat > ui/__init__.py << 'EOF'
"""PTC user interface components."""

from .main_window import MainWindow
from .workspace import WelcomeWidget, WorkspaceWidget

__all__ = ["MainWindow", "WelcomeWidget", "WorkspaceWidget"]
EOF

cat > ui/wizards/__init__.py << 'EOF'
"""PTC wizard dialogs."""

from .new_project import NewProjectWizard
from .adopt_project import AdoptProjectWizard

__all__ = ["NewProjectWizard", "AdoptProjectWizard"]
EOF

# Clean up the old __init__.py in root if it exists
rm -f __init__.py

# Clean up the mnt folder (artifact from download)
rm -rf mnt

echo "Done! Structure should now be:"
echo ""
ls -la
echo ""
echo "ui folder:"
ls -la ui/
echo ""
echo "core folder:"
ls -la core/
echo ""
echo "Try running: python3 main.py"

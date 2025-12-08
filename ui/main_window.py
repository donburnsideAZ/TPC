"""
Main window for TPC.

Layout:
┌─────────────────┬────────────────────────────────────┐
│   PROJECTS      │         WORKSPACE                  │
│                 │                                    │
│  [Voxsmith]     │   (changes based on selection)     │
│  [Flowpath] ◄───│                                    │
│  [Voxprep]      │                                    │
│                 │                                    │
│  ─────────────  │                                    │
│  [📦 Build]     │                                    │
│  ─────────────  │                                    │
│  [+ New]        │                                    │
│  [→ Import]     │                                    │
│  [↓ Adopt]      │                                    │
│                 │                                    │
│  ⚙ Settings     │                                    │
└─────────────────┴────────────────────────────────────┘
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QStackedWidget, QFrame, QSplitter, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QScreen, QGuiApplication

from core import __version__
from core.project import Project, find_ptc_projects, DEFAULT_PROJECTS_ROOT
from ui.wizards.new_project import NewProjectWizard
from ui.wizards.adopt_project import AdoptProjectWizard
from ui.wizards.import_project import ImportProjectWizard
from ui.workspace import WorkspaceWidget, WelcomeWidget
from ui.pack_workspace import PackWorkspace


class ProjectListItem(QListWidgetItem):
    """A project item in the sidebar list."""
    
    def __init__(self, project: Project):
        super().__init__(project.name)
        self.project = project
        
        # Show unsaved indicator
        if project.has_unsaved_changes:
            self.setText(f"● {project.name}")


class MainWindow(QMainWindow):
    """The main TPC window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(f"TPC - Track Pack Click v{__version__}")
        self.setup_window_size()
        
        # Track current project
        self.current_project: Project | None = None
        
        # Build the UI
        self.setup_ui()
        
        # Load existing projects
        self.refresh_project_list()
    
    def setup_window_size(self):
        """Set window to 750px wide, centered."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            width = 750
            height = max(900, int(geometry.height() * 0.8))
            x = (geometry.width() - width) // 2
            y = (geometry.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            self.resize(850, 700)
        
        self.setMinimumSize(850, 700)
    
    def setup_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for resizable sidebar
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === SIDEBAR ===
        sidebar = self.create_sidebar()
        splitter.addWidget(sidebar)
        
        # === WORKSPACE ===
        self.workspace_stack = QStackedWidget()
        
        # Welcome screen (shown when no project selected)
        self.welcome_widget = WelcomeWidget()
        self.welcome_widget.new_clicked.connect(self.on_new_project)
        self.welcome_widget.adopt_clicked.connect(self.on_adopt_project)
        self.workspace_stack.addWidget(self.welcome_widget)
        
        # Project workspace (shown when project selected)
        self.workspace_widget = WorkspaceWidget()
        self.workspace_widget.project_changed.connect(self.refresh_project_list)
        self.workspace_stack.addWidget(self.workspace_widget)
        
        # Pack workspace (shown when Build is clicked)
        self.pack_workspace = PackWorkspace()
        self.pack_workspace.back_clicked.connect(self.on_back_from_pack)
        self.workspace_stack.addWidget(self.pack_workspace)
        
        splitter.addWidget(self.workspace_stack)
        
        # Set initial splitter sizes (sidebar: 250px, workspace: rest)
        splitter.setSizes([250, 950])
        splitter.setStretchFactor(0, 0)  # Sidebar doesn't stretch
        splitter.setStretchFactor(1, 1)  # Workspace stretches
        
        layout.addWidget(splitter)
        
        # Apply styling
        self.apply_styles()
    
    def create_sidebar(self) -> QFrame:
        """Create the project list sidebar."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(350)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Projects")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)
        
        # Project list
        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.itemClicked.connect(self.on_project_selected)
        layout.addWidget(self.project_list, 1)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        
        # Build button (operates on selected project)
        self.btn_build = QPushButton(">> Build for Distribution")
        self.btn_build.setObjectName("sidebarButtonBuild")
        self.btn_build.setToolTip("Package project for distribution")
        self.btn_build.clicked.connect(self.on_build)
        layout.addWidget(self.btn_build)
        print(f">>> Build button added, visible={self.btn_build.isVisible()}")
        
        # Separator before project management
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setObjectName("separator")
        layout.addWidget(separator2)
        
        # Action buttons
        btn_new = QPushButton("+ New Project")
        btn_new.setObjectName("sidebarButton")
        btn_new.clicked.connect(self.on_new_project)
        layout.addWidget(btn_new)
        
        btn_import = QPushButton("→ Import Project")
        btn_import.setObjectName("sidebarButton")
        btn_import.clicked.connect(self.on_import_project)
        layout.addWidget(btn_import)
        
        btn_adopt = QPushButton("↓ Adopt Script")
        btn_adopt.setObjectName("sidebarButton")
        btn_adopt.clicked.connect(self.on_adopt_project)
        layout.addWidget(btn_adopt)
        
        # Settings (future)
        layout.addStretch()
        
        btn_settings = QPushButton("⚙ Settings")
        btn_settings.setObjectName("sidebarButtonSecondary")
        btn_settings.clicked.connect(self.on_settings)
        layout.addWidget(btn_settings)
        
        return sidebar
    
    def apply_styles(self):
        """Apply the PTC visual style - friendly, clean, not corporate."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            
            #sidebar {
                background-color: #f1f1f1;
                border-right: 1px solid #e0e0e0;
            }
            
            #sidebarHeader {
                color: #222222;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0;
            }
            
            #projectList {
                background-color: transparent;
                border: none;
                color: #333333;
                font-size: 13px;
                outline: none;
            }
            
            #projectList::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            #projectList::item:hover {
                background-color: #e4e4e4;
            }
            
            #projectList::item:selected {
                background-color: #d0d0d0;
                color: #000000;
            }
            
            #separator {
                background-color: #e0e0e0;
                max-height: 1px;
                margin: 8px 0;
            }
            
            #sidebarButton {
                background-color: #0f3460;
                color: #e8e8e8;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
                text-align: left;
            }
            
            #sidebarButton:hover {
                background-color: #1a4a7a;
            }
            
            #sidebarButton:pressed {
                background-color: #0a2540;
            }
            
            #sidebarButtonSecondary {
                background-color: transparent;
                color: #666666;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
                text-align: left;
            }
            
            #sidebarButtonSecondary:hover {
                background-color: #e4e4e4;
                color: #333333;
            }
            
            #sidebarButtonBuild {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
                text-align: left;
                font-weight: 500;
            }
            
            #sidebarButtonBuild:hover {
                background-color: #3ddc81;
            }
            
            #sidebarButtonBuild:pressed {
                background-color: #27ae60;
            }
        """)
    
    def refresh_project_list(self):
        """Reload the project list from disk."""
        self.project_list.clear()
        
        projects = find_ptc_projects()
        
        for project in projects:
            item = ProjectListItem(project)
            self.project_list.addItem(item)
        
        # Re-select current project if it still exists
        if self.current_project:
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if isinstance(item, ProjectListItem):
                    if item.project.path == self.current_project.path:
                        self.project_list.setCurrentItem(item)
                        break
    
    def on_project_selected(self, item: QListWidgetItem):
        """Handle project selection from the list."""
        if isinstance(item, ProjectListItem):
            self.current_project = item.project
            self.workspace_widget.set_project(item.project)
            self.workspace_stack.setCurrentWidget(self.workspace_widget)
    
    def on_new_project(self):
        """Show the New Project wizard."""
        wizard = NewProjectWizard(self)
        if wizard.exec():
            project = wizard.created_project
            if project:
                self.refresh_project_list()
                self.current_project = project
                self.workspace_widget.set_project(project)
                self.workspace_stack.setCurrentWidget(self.workspace_widget)
    
    def on_import_project(self):
        """Show the Import Project wizard."""
        wizard = ImportProjectWizard(self)
        if wizard.exec():
            project = wizard.imported_project
            if project:
                self.refresh_project_list()
                self.current_project = project
                self.workspace_widget.set_project(project)
                self.workspace_stack.setCurrentWidget(self.workspace_widget)
    
    def on_adopt_project(self):
        """Show the Adopt Project wizard."""
        wizard = AdoptProjectWizard(self)
        if wizard.exec():
            project = wizard.adopted_project
            if project:
                self.refresh_project_list()
                self.current_project = project
                self.workspace_widget.set_project(project)
                self.workspace_stack.setCurrentWidget(self.workspace_widget)
    
    def on_build(self):
        """Show the Pack workspace for building the current project."""
        self.pack_workspace.set_project(self.current_project)
        self.workspace_stack.setCurrentWidget(self.pack_workspace)
    
    def on_back_from_pack(self):
        """Return from Pack workspace to project workspace."""
        if self.current_project:
            self.workspace_stack.setCurrentWidget(self.workspace_widget)
        else:
            self.workspace_stack.setCurrentWidget(self.welcome_widget)
    
    def on_settings(self):
        """Show settings (future feature)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Settings are coming in a future update.\n\n"
            "For now, everything just works. ✨"
        )

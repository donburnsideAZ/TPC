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
│                 │                                    │
│  ⚙ Settings     │                                    │
└─────────────────┴────────────────────────────────────┘
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QStackedWidget, QFrame, QSplitter, QFileDialog,
    QMessageBox, QMenu, QMenuBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QScreen, QGuiApplication, QAction

from core import __version__
from core import Project, find_tpc_projects, DEFAULT_PROJECTS_ROOT, remove_from_tpc
from ui.wizards.new_project import NewProjectWizard
from ui.wizards.import_project import ImportProjectWizard
from ui.wizards.clone_github import CloneFromGitHubWizard
from ui.workspace_v3 import WorkspaceWidget, WelcomeWidget
from ui.pack_workspace import PackWorkspace
from ui.settings_dialog import SettingsDialog


class ProjectListItem(QListWidgetItem):
    """A project item in the sidebar list."""
    
    def __init__(self, project: Project):
        super().__init__(project.name)
        self.project = project
        # No more dots - they were causing anxiety about git state
        # that didn't reflect meaningful user changes


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
        """Set window to 1100px wide, centered - wider for 2-column layout."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            width = 1100
            height = min(700, int(geometry.height() * 0.75))
            x = (geometry.width() - width) // 2
            y = (geometry.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            self.resize(1100, 700)
        
        self.setMinimumSize(900, 550)
    
    def setup_ui(self):
        """Build the main UI layout."""
        # Create menu bar first
        self.setup_menu_bar()
        
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
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self.on_project_context_menu)
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
        
        # Settings (future)
        layout.addStretch()
        
        btn_settings = QPushButton("⚙ Settings")
        btn_settings.setObjectName("sidebarButtonSecondary")
        btn_settings.clicked.connect(self.on_settings)
        layout.addWidget(btn_settings)
        
        return sidebar
    
    def setup_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # TPC Menu (app-level actions)
        tpc_menu = menubar.addMenu("TPC")
        
        # Quit action (macOS style)
        quit_action = QAction("Quit TPC", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        tpc_menu.addAction(quit_action)
        
        # Project Menu
        project_menu = menubar.addMenu("Project")
        
        new_action = QAction("New Project...", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_new_project)
        project_menu.addAction(new_action)
        
        import_action = QAction("Import Project...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.on_import_project)
        project_menu.addAction(import_action)
        
        clone_action = QAction("Clone from GitHub...", self)
        clone_action.setShortcut("Ctrl+Shift+G")
        clone_action.triggered.connect(self.on_clone_github)
        project_menu.addAction(clone_action)
        
        project_menu.addSeparator()
        
        remove_action = QAction("Remove from TPC...", self)
        remove_action.triggered.connect(self.on_remove_current_project)
        project_menu.addAction(remove_action)
        
        project_menu.addSeparator()
        
        # Open TPC Projects folder - show actual path
        import platform
        projects_path = str(DEFAULT_PROJECTS_ROOT)
        open_folder_action = QAction(f"Open {projects_path}", self)
        open_folder_action.triggered.connect(self.on_open_projects_folder)
        project_menu.addAction(open_folder_action)
        
        # Help Menu
        help_menu = menubar.addMenu("Help")
        
        # Settings action
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.on_settings)
        help_menu.addAction(settings_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction(f"About TPC v{__version__}", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
    
    def on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About TPC v{__version__}",
            f"<h3>TPC - Track Pack Click</h3>"
            f"<p>Version {__version__}</p>"
            f"<p>The packaging tool for people who just want to ship.</p>"
            f"<p><i>\"I just want to hand someone an installer and say 'here, this works.'\"</i></p>"
        )
    
    def on_project_context_menu(self, position):
        """Show context menu when right-clicking a project."""
        item = self.project_list.itemAt(position)
        
        if not isinstance(item, ProjectListItem):
            return
        
        project = item.project
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                color: #333333;
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e8e8e8;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e0e0e0;
                margin: 4px 8px;
            }
        """)
        
        # Show in Finder/Explorer - platform-aware label
        import platform
        if platform.system() == "Darwin":
            show_label = "Show in Finder"
        elif platform.system() == "Windows":
            show_label = "Show in Explorer"
        else:
            show_label = "Show in File Manager"
        
        show_action = menu.addAction(show_label)
        show_action.triggered.connect(lambda: self.on_show_in_finder(project))
        
        menu.addSeparator()
        
        # Set Main File
        set_main_action = menu.addAction("Set Main File...")
        set_main_action.triggered.connect(lambda: self.on_set_main_file(project))
        
        menu.addSeparator()
        
        # Remove from TPC
        remove_action = menu.addAction("Remove from TPC...")
        remove_action.triggered.connect(lambda: self.on_remove_project(project))
        
        # Show the menu at cursor position
        menu.exec(self.project_list.mapToGlobal(position))
    
    def on_show_in_finder(self, project: Project):
        """Open the project folder in Finder/Explorer."""
        import subprocess
        import platform
        from core import subprocess_args
        
        path = str(project.path)
        
        if platform.system() == "Darwin":
            subprocess.run(["open", path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", path], **subprocess_args())
        else:
            subprocess.run(["xdg-open", path])
    
    def on_set_main_file(self, project: Project):
        """Let user choose the main Python file for this project."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Start in the project folder
        start_dir = str(project.path)
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            f"Set Main File for {project.name}",
            start_dir,
            "Python Files (*.py *.pyw)"
        )
        
        if not filepath:
            return  # User cancelled
        
        from pathlib import Path
        selected_path = Path(filepath)
        
        # Make sure the file is inside the project folder
        try:
            relative = selected_path.relative_to(project.path)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "The main file must be inside the project folder.\n\n"
                f"Project folder: {project.path}"
            )
            return
        
        # Update the project config
        old_main = project.main_file
        project.main_file = str(relative)
        project.save_config()
        
        QMessageBox.information(
            self,
            "Main File Updated",
            f"Main file changed from:\n  {old_main}\n\nTo:\n  {relative}\n\n"
            f"The Launch button will now run this file."
        )
        
        # Refresh if this is the current project
        if self.current_project and self.current_project.path == project.path:
            self.current_project = project
            self.workspace_widget.set_project(project)
    
    def on_open_projects_folder(self):
        """Open the TPC Projects folder in Finder/Explorer."""
        import subprocess
        import platform
        from core import subprocess_args
        
        # Create the folder if it doesn't exist yet
        DEFAULT_PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        
        path = str(DEFAULT_PROJECTS_ROOT)
        
        if platform.system() == "Darwin":
            subprocess.run(["open", path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", path], **subprocess_args())
        else:
            subprocess.run(["xdg-open", path])
    
    def on_remove_project(self, project: Project):
        """Remove a project from TPC (keeps all files)."""
        reply = QMessageBox.question(
            self,
            "Remove from TPC?",
            f"Remove '{project.name}' from TPC?\n\n"
            f"This will:\n"
            f"  • Stop tracking this project in TPC\n"
            f"  • Delete the .tpc config folder\n\n"
            f"This will NOT:\n"
            f"  • Delete your code files\n"
            f"  • Delete version history (.git)\n"
            f"  • Affect GitHub in any way\n\n"
            f"You can always re-import the project later.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = remove_from_tpc(project.path)
            
            if success:
                # Clear selection if this was the current project
                if self.current_project and self.current_project.path == project.path:
                    self.current_project = None
                    self.workspace_stack.setCurrentWidget(self.welcome_widget)
                
                self.refresh_project_list()
                
                QMessageBox.information(
                    self,
                    "Removed",
                    message
                )
            else:
                QMessageBox.warning(
                    self,
                    "Couldn't Remove",
                    message
                )
    
    def on_remove_current_project(self):
        """Remove the currently selected project (menu bar action)."""
        if self.current_project:
            self.on_remove_project(self.current_project)
        else:
            QMessageBox.information(
                self,
                "No Project Selected",
                "Select a project first, then use this option to remove it from TPC."
            )
    
    def apply_styles(self):
        """Apply the TPC visual style - friendly, clean, not corporate."""
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
        
        projects = find_tpc_projects()
        
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
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def on_clone_github(self):
        """Show the Clone from GitHub wizard."""
        wizard = CloneFromGitHubWizard(self)
        if wizard.exec():
            project = wizard.cloned_project
            if project:
                self.refresh_project_list()
                self.current_project = project
                self.workspace_widget.set_project(project)
                self.workspace_stack.setCurrentWidget(self.workspace_widget)

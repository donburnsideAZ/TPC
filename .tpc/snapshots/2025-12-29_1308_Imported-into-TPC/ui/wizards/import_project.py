"""
Import Project Wizard for TPC.

For projects that already have a home - we just add TPC management
on top without moving or copying anything.

Supports:
- Python projects (with main file selection)
- Folder projects (for non-Python content like Obsidian vaults, HTML sites, etc.)

Flow:
1. Where's your project? (folder picker)
2. Is this a Python project? (auto-detect)
3. What's the main file? (if Python)
4. Done! TPC now manages it.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QWidget,
    QComboBox, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt

from core import Project, DEFAULT_PROJECTS_ROOT, register_project_path


def find_python_files(folder: Path) -> list[str]:
    """Find all Python files in a folder (not recursive)."""
    py_files = []
    try:
        for f in folder.iterdir():
            if f.is_file() and f.suffix in ('.py', '.pyw'):
                py_files.append(f.name)
    except PermissionError:
        pass
    return sorted(py_files)


def guess_main_file(py_files: list[str]) -> str:
    """Try to guess which file is the main entry point."""
    common_names = ['main.py', 'app.py', '__main__.py', 'run.py', 'start.py']
    
    for name in common_names:
        if name in py_files:
            return name
    
    return py_files[0] if py_files else "main.py"


def has_git_history(folder: Path) -> bool:
    """Check if the folder has an existing git repository."""
    return (folder / ".git").is_dir()


def is_already_tpc_project(folder: Path) -> bool:
    """Check if the folder is already a TPC project."""
    tpc_config = folder / ".tpc" / "project.json"
    ptc_config = folder / ".ptc" / "project.json"
    return tpc_config.exists() or ptc_config.exists()


def is_project_in_sidebar(folder: Path) -> bool:
    """Check if a project is showing in the sidebar."""
    from core.project_v3 import get_known_project_paths, DEFAULT_PROJECTS_ROOT
    
    try:
        folder.relative_to(DEFAULT_PROJECTS_ROOT)
        return True
    except ValueError:
        pass
    
    return folder in get_known_project_paths()


class ImportProjectWizard(QDialog):
    """Wizard for importing an existing project folder into TPC."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.imported_project: Project | None = None
        self.selected_folder: Path | None = None
        self.python_files: list[str] = []
        self._is_reregister = False
        
        self.setWindowTitle("Import Project")
        self.setModal(True)
        self.setMinimumSize(550, 520)
        self.resize(600, 580)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Already have a project folder?")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        subheader = QLabel(
            "Point us at it and we'll take it from here. Nothing gets moved or copied."
        )
        subheader.setObjectName("wizardSubheader")
        layout.addWidget(subheader)
        
        # Step 1: Select folder
        folder_section = QWidget()
        folder_layout = QVBoxLayout(folder_section)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        
        folder_label = QLabel("Where's your project?")
        folder_label.setObjectName("fieldLabel")
        folder_layout.addWidget(folder_label)
        
        folder_row = QWidget()
        folder_row_layout = QHBoxLayout(folder_row)
        folder_row_layout.setContentsMargins(0, 0, 0, 0)
        folder_row_layout.setSpacing(8)
        
        self.folder_display = QLabel("No folder selected")
        self.folder_display.setObjectName("folderDisplay")
        self.folder_display.setWordWrap(True)
        folder_row_layout.addWidget(self.folder_display, 1)
        
        btn_browse = QPushButton("Browse")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.clicked.connect(self.browse_folder)
        folder_row_layout.addWidget(btn_browse)
        
        folder_layout.addWidget(folder_row)
        layout.addWidget(folder_section)
        
        # Status message
        self.status_message = QLabel("")
        self.status_message.setObjectName("statusMessage")
        self.status_message.setWordWrap(True)
        layout.addWidget(self.status_message)
        
        # Step 2: Project name
        name_section = QWidget()
        name_layout = QVBoxLayout(name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        
        name_label = QLabel("Project name")
        name_label.setObjectName("fieldLabel")
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("fieldInput")
        self.name_input.setPlaceholderText("My Project")
        name_layout.addWidget(self.name_input)
        
        layout.addWidget(name_section)
        
        # Step 3: Project type selection
        type_section = QWidget()
        type_layout = QVBoxLayout(type_section)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)
        
        type_label = QLabel("What kind of project is this?")
        type_label.setObjectName("fieldLabel")
        type_layout.addWidget(type_label)
        
        self.type_group = QButtonGroup(self)
        
        self.radio_python = QRadioButton("Python project — I can run a .py file")
        self.radio_python.setObjectName("typeRadio")
        self.radio_python.setChecked(True)
        self.radio_python.toggled.connect(self.on_type_changed)
        self.type_group.addButton(self.radio_python)
        type_layout.addWidget(self.radio_python)
        
        self.radio_folder = QRadioButton("Folder project — just track files (Obsidian, HTML, notes, etc.)")
        self.radio_folder.setObjectName("typeRadio")
        self.radio_folder.toggled.connect(self.on_type_changed)
        self.type_group.addButton(self.radio_folder)
        type_layout.addWidget(self.radio_folder)
        
        layout.addWidget(type_section)
        
        # Step 4: Main file selection (Python only)
        self.main_section = QWidget()
        main_layout = QVBoxLayout(self.main_section)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        main_label = QLabel("Which file runs the show?")
        main_label.setObjectName("fieldLabel")
        main_layout.addWidget(main_label)
        
        self.main_file_combo = QComboBox()
        self.main_file_combo.setObjectName("fieldCombo")
        main_layout.addWidget(self.main_file_combo)
        
        layout.addWidget(self.main_section)
        
        layout.addStretch()
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        self.btn_import = QPushButton("Import Project")
        self.btn_import.setObjectName("btnCreate")
        self.btn_import.clicked.connect(self.import_project)
        self.btn_import.setEnabled(False)
        btn_layout.addWidget(self.btn_import)
        
        layout.addWidget(btn_row)
        
        self.apply_styles()
    
    def on_type_changed(self):
        """Show/hide main file selection based on project type."""
        is_python = self.radio_python.isChecked()
        self.main_section.setVisible(is_python)
    
    def browse_folder(self):
        """Open folder picker."""
        start_dir = str(Path.home() / "Documents")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.selected_folder = Path(folder)
            self.folder_display.setText(str(self.selected_folder))
            self.analyze_folder()
    
    def analyze_folder(self):
        """Analyze the selected folder and update UI accordingly."""
        if not self.selected_folder:
            return
        
        has_tpc_config = is_already_tpc_project(self.selected_folder)
        is_in_sidebar = is_project_in_sidebar(self.selected_folder)
        
        if has_tpc_config and is_in_sidebar:
            self.status_message.setText(
                "⚠️ This folder is already a TPC project. "
                "You can open it from the sidebar instead."
            )
            self.status_message.setStyleSheet("color: #e67e22; font-size: 13px;")
            self.btn_import.setEnabled(False)
            return
        
        if has_tpc_config and not is_in_sidebar:
            self.status_message.setText(
                "✓ Found existing TPC project — we'll add it back to your sidebar."
            )
            self.status_message.setStyleSheet("color: #27ae60; font-size: 13px;")
            self._is_reregister = True
            
            try:
                existing_project = Project.load(self.selected_folder)
                self.name_input.setText(existing_project.name)
                
                # Set project type from existing config
                if existing_project.project_type == "folder":
                    self.radio_folder.setChecked(True)
                else:
                    self.radio_python.setChecked(True)
                
                self.python_files = find_python_files(self.selected_folder)
                self.main_file_combo.clear()
                
                if self.python_files:
                    self.main_file_combo.addItems(self.python_files)
                    if existing_project.main_file in self.python_files:
                        idx = self.python_files.index(existing_project.main_file)
                        self.main_file_combo.setCurrentIndex(idx)
                else:
                    self.main_file_combo.addItem(existing_project.main_file)
                
                self.btn_import.setEnabled(True)
                self.btn_import.setText("Add to Sidebar")
                return
            except Exception:
                pass
        
        # Normal new import flow
        self._is_reregister = False
        self.btn_import.setText("Import Project")
        
        self.name_input.setText(self.selected_folder.name)
        
        if has_git_history(self.selected_folder):
            self.status_message.setText(
                "✓ Found existing version history — we'll keep all of it."
            )
            self.status_message.setStyleSheet("color: #27ae60; font-size: 13px;")
        else:
            self.status_message.setText(
                "No version history found — we'll start tracking from here."
            )
            self.status_message.setStyleSheet("color: #666666; font-size: 13px;")
        
        self.python_files = find_python_files(self.selected_folder)
        self.main_file_combo.clear()
        
        if self.python_files:
            self.main_file_combo.addItems(self.python_files)
            guessed = guess_main_file(self.python_files)
            index = self.python_files.index(guessed) if guessed in self.python_files else 0
            self.main_file_combo.setCurrentIndex(index)
            self.radio_python.setChecked(True)
        else:
            self.main_file_combo.addItem("(no Python files found)")
            self.radio_folder.setChecked(True)
        
        self.btn_import.setEnabled(True)
    
    def import_project(self):
        """Validate and import the project."""
        if not self.selected_folder:
            QMessageBox.warning(self, "No Folder Selected", 
                "Please select a project folder to import.")
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required",
                "Every project needs a name.\n\n"
                "We've suggested one based on the folder name.")
            self.name_input.setFocus()
            return
        
        project_type = "python" if self.radio_python.isChecked() else "folder"
        
        main_file = self.main_file_combo.currentText()
        if main_file == "(no Python files found)":
            main_file = "main.py"
        
        try:
            if self._is_reregister:
                from core.project_v3 import register_project_path
                self.imported_project = Project.load(self.selected_folder)
                register_project_path(self.selected_folder)
            else:
                self.imported_project = Project.import_existing(
                    folder=self.selected_folder,
                    name=name,
                    main_file=main_file,
                    project_type=project_type
                )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Something Went Wrong",
                f"Couldn't import the project:\n\n{e}\n\n"
                "Check that you have write access to the folder.")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            
            #wizardHeader {
                color: #333333; font-size: 22px; font-weight: 600;
            }
            
            #wizardSubheader {
                color: #888888; font-size: 14px; margin-bottom: 8px;
            }
            
            #fieldLabel {
                color: #555555; font-size: 14px; font-weight: 500;
            }
            
            #fieldInput {
                background-color: #ffffff; border: 1px solid #cccccc;
                border-radius: 6px; padding: 10px 12px;
                color: #333333; font-size: 15px; min-height: 20px;
            }
            #fieldInput:focus { border-color: #4a9eff; }
            
            #fieldCombo {
                background-color: #ffffff; border: 1px solid #cccccc;
                border-radius: 6px; padding: 10px 12px;
                color: #333333; font-size: 14px; min-height: 20px;
            }
            #fieldCombo:focus { border-color: #4a9eff; }
            #fieldCombo::drop-down { border: none; padding-right: 8px; }
            
            #folderDisplay {
                color: #666666; font-size: 13px;
                background-color: #f5f5f5; padding: 10px 12px; border-radius: 6px;
            }
            
            #statusMessage { font-size: 13px; padding: 8px 0; }
            
            #typeRadio { font-size: 13px; color: #444444; padding: 4px 0; }
            
            #btnBrowse {
                background-color: #e8e8e8; color: #555555; border: none;
                padding: 10px 16px; border-radius: 6px; font-size: 13px;
            }
            #btnBrowse:hover { background-color: #d8d8d8; }
            
            #btnCancel {
                background-color: transparent; color: #666666;
                border: 1px solid #cccccc; padding: 12px 24px;
                border-radius: 6px; font-size: 14px;
            }
            #btnCancel:hover { background-color: #f0f0f0; color: #333333; }
            
            #btnCreate {
                background-color: #4a9eff; color: white; border: none;
                padding: 12px 24px; border-radius: 6px;
                font-size: 14px; font-weight: 500;
            }
            #btnCreate:hover { background-color: #5aafff; }
            #btnCreate:pressed { background-color: #3a8eef; }
            #btnCreate:disabled { background-color: #cccccc; color: #888888; }
        """)

"""
Import Project Wizard for PTC.

For projects that already have a home - we just add PTC management
on top without moving or copying anything.

Flow:
1. Where's your project? (folder picker)
2. What's the main file? (auto-detect or ask)
3. Done! PTC now manages it.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QWidget,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt

from core.project import Project, DEFAULT_PROJECTS_ROOT


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
    # Common main file names in priority order
    common_names = ['main.py', 'app.py', '__main__.py', 'run.py', 'start.py']
    
    for name in common_names:
        if name in py_files:
            return name
    
    # If nothing common, return the first one
    return py_files[0] if py_files else "main.py"


def has_git_history(folder: Path) -> bool:
    """Check if the folder has an existing git repository."""
    return (folder / ".git").is_dir()


def is_already_ptc_project(folder: Path) -> bool:
    """Check if the folder is already a PTC project."""
    return (folder / ".ptc" / "project.json").exists()


class ImportProjectWizard(QDialog):
    """Wizard for importing an existing project folder into PTC."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.imported_project: Project | None = None
        self.selected_folder: Path | None = None
        self.python_files: list[str] = []
        
        self.setWindowTitle("Import Project")
        self.setModal(True)
        self.setMinimumSize(550, 450)
        self.resize(600, 500)
        
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
        
        # Status message (shows git detection, etc.)
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
        
        # Step 3: Main file selection
        main_section = QWidget()
        main_layout = QVBoxLayout(main_section)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        main_label = QLabel("Which file runs the show?")
        main_label.setObjectName("fieldLabel")
        main_layout.addWidget(main_label)
        
        self.main_file_combo = QComboBox()
        self.main_file_combo.setObjectName("fieldCombo")
        main_layout.addWidget(self.main_file_combo)
        
        layout.addWidget(main_section)
        
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
    
    def browse_folder(self):
        """Open folder picker."""
        # Start at common project locations
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
        
        # Check if already a PTC project
        if is_already_ptc_project(self.selected_folder):
            self.status_message.setText(
                "⚠️ This folder is already a PTC project. "
                "You can open it from the sidebar instead."
            )
            self.status_message.setStyleSheet("color: #e67e22; font-size: 13px;")
            self.btn_import.setEnabled(False)
            return
        
        # Set project name from folder name
        self.name_input.setText(self.selected_folder.name)
        
        # Check for git history
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
        
        # Find Python files
        self.python_files = find_python_files(self.selected_folder)
        
        self.main_file_combo.clear()
        
        if self.python_files:
            self.main_file_combo.addItems(self.python_files)
            
            # Try to guess the main file
            guessed = guess_main_file(self.python_files)
            index = self.python_files.index(guessed) if guessed in self.python_files else 0
            self.main_file_combo.setCurrentIndex(index)
            
            self.btn_import.setEnabled(True)
        else:
            self.main_file_combo.addItem("(no Python files found)")
            self.btn_import.setEnabled(True)  # Still allow import, they can add files later
    
    def import_project(self):
        """Validate and import the project."""
        if not self.selected_folder:
            QMessageBox.warning(
                self,
                "No Folder Selected",
                "Please select a project folder to import."
            )
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Every project needs a name.\n\n"
                "We've suggested one based on the folder name."
            )
            self.name_input.setFocus()
            return
        
        # Get selected main file
        main_file = self.main_file_combo.currentText()
        if main_file == "(no Python files found)":
            main_file = "main.py"  # Default, they'll create it
        
        try:
            self.imported_project = Project.import_existing(
                folder=self.selected_folder,
                name=name,
                main_file=main_file
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Something Went Wrong",
                f"Couldn't import the project:\n\n{e}\n\n"
                "Check that you have write access to the folder."
            )
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            #wizardHeader {
                color: #333333;
                font-size: 22px;
                font-weight: 600;
            }
            
            #wizardSubheader {
                color: #888888;
                font-size: 14px;
                margin-bottom: 8px;
            }
            
            #fieldLabel {
                color: #555555;
                font-size: 14px;
                font-weight: 500;
            }
            
            #fieldInput {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                color: #333333;
                font-size: 15px;
            }
            
            #fieldInput:focus {
                border-color: #4a9eff;
            }
            
            #fieldCombo {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                color: #333333;
                font-size: 14px;
            }
            
            #fieldCombo:focus {
                border-color: #4a9eff;
            }
            
            #fieldCombo::drop-down {
                border: none;
                padding-right: 8px;
            }
            
            #folderDisplay {
                color: #666666;
                font-size: 13px;
                background-color: #f5f5f5;
                padding: 10px 12px;
                border-radius: 6px;
            }
            
            #statusMessage {
                font-size: 13px;
                padding: 8px 0;
            }
            
            #btnBrowse {
                background-color: #e8e8e8;
                color: #555555;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #btnBrowse:hover {
                background-color: #d8d8d8;
            }
            
            #btnCancel {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
            }
            
            #btnCancel:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #btnCreate {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            
            #btnCreate:hover {
                background-color: #5aafff;
            }
            
            #btnCreate:pressed {
                background-color: #3a8eef;
            }
            
            #btnCreate:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)

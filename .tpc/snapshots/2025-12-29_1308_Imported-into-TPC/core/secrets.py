"""
Secrets Detection for TPC.

Scans project files for potentially sensitive files that shouldn't
be backed up to GitHub. Filename-based detection for v1.

This runs before the first GitHub backup to warn users about
files that might contain API keys, passwords, or other secrets.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class SecretFinding:
    """A potentially sensitive file found in the project."""
    file_path: Path
    relative_path: str
    reason: str
    severity: str  # "high", "medium", "low"


# Exact filename matches (case-insensitive)
SENSITIVE_FILENAMES = {
    # Environment files
    ".env": ("Environment file - often contains API keys and secrets", "high"),
    ".env.local": ("Local environment file - often contains secrets", "high"),
    ".env.development": ("Development environment file", "medium"),
    ".env.production": ("Production environment file - likely contains secrets", "high"),
    ".env.staging": ("Staging environment file", "medium"),
    ".env.test": ("Test environment file", "low"),
    
    # Credential files
    "credentials.json": ("Credentials file - may contain API keys", "high"),
    "secrets.json": ("Secrets file - likely contains sensitive data", "high"),
    "secrets.yaml": ("Secrets file - likely contains sensitive data", "high"),
    "secrets.yml": ("Secrets file - likely contains sensitive data", "high"),
    ".secrets": ("Secrets file", "high"),
    
    # Key files
    ".pem": ("Private key file", "high"),
    "id_rsa": ("SSH private key", "high"),
    "id_dsa": ("SSH private key", "high"),
    "id_ecdsa": ("SSH private key", "high"),
    "id_ed25519": ("SSH private key", "high"),
    
    # Cloud credentials
    ".aws": ("AWS credentials directory", "high"),
    ".netrc": ("Network credentials file", "high"),
    ".npmrc": ("NPM config - may contain auth tokens", "medium"),
    ".pypirc": ("PyPI config - may contain auth tokens", "medium"),
    
    # Database
    ".sqlite": ("SQLite database - may contain user data", "low"),
    ".db": ("Database file - may contain user data", "low"),
    
    # Config files that sometimes have secrets
    "config.json": ("Config file - check for hardcoded secrets", "low"),
    "settings.json": ("Settings file - check for hardcoded secrets", "low"),
}

# Filename patterns (regex)
SENSITIVE_PATTERNS = [
    # Environment files with any suffix
    (r"^\.env\..+$", "Environment file variant", "medium"),
    
    # Key files
    (r".*\.pem$", "PEM key file", "high"),
    (r".*\.key$", "Private key file", "high"),
    (r".*\.p12$", "PKCS12 certificate", "high"),
    (r".*\.pfx$", "PKCS12 certificate", "high"),
    (r".*\.jks$", "Java keystore", "high"),
    
    # Token/secret in filename
    (r".*secret.*", "Filename contains 'secret'", "medium"),
    (r".*token.*\.json$", "Token file", "medium"),
    (r".*password.*", "Filename contains 'password'", "medium"),
    (r".*credential.*", "Filename contains 'credential'", "medium"),
    (r".*api[_-]?key.*", "API key file", "high"),
    
    # Backup files that might have secrets
    (r".*\.bak$", "Backup file - may contain old secrets", "low"),
]

# Directories to skip entirely
SKIP_DIRECTORIES = {
    ".git", ".tpc", ".ptc", "__pycache__", "node_modules",
    "venv", ".venv", "env", ".env",  # virtual environments, not .env files
    "TPC Builds", "dist", "build",
}


def scan_for_secrets(
    project_path: Path,
    ignore_patterns: Optional[list[str]] = None
) -> list[SecretFinding]:
    """
    Scan a project directory for potentially sensitive files.
    
    Args:
        project_path: Root path of the project
        ignore_patterns: List of patterns to ignore (from project config)
    
    Returns:
        List of SecretFinding objects for files that might contain secrets
    """
    findings = []
    ignore_patterns = ignore_patterns or []
    
    def should_ignore(path: Path) -> bool:
        """Check if a path should be ignored."""
        rel_path = str(path.relative_to(project_path))
        
        for pattern in ignore_patterns:
            # Simple glob-style matching
            if pattern.endswith('/'):
                # Directory pattern
                if rel_path.startswith(pattern.rstrip('/')):
                    return True
            elif '*' in pattern:
                # Wildcard pattern
                import fnmatch
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
                if fnmatch.fnmatch(path.name, pattern):
                    return True
            else:
                # Exact match
                if rel_path == pattern or path.name == pattern:
                    return True
        
        return False
    
    def scan_directory(directory: Path):
        """Recursively scan a directory."""
        try:
            for item in directory.iterdir():
                # Skip hidden TPC/git directories
                if item.name in SKIP_DIRECTORIES:
                    continue
                
                # Skip if matches ignore patterns
                if should_ignore(item):
                    continue
                
                if item.is_dir():
                    # Check if directory name itself is sensitive
                    check_item(item)
                    # Recurse into directory
                    scan_directory(item)
                else:
                    check_item(item)
        except PermissionError:
            pass
    
    def check_item(item: Path):
        """Check a single file or directory for sensitivity."""
        name_lower = item.name.lower()
        rel_path = str(item.relative_to(project_path))
        
        # Check exact filename matches
        if name_lower in SENSITIVE_FILENAMES:
            reason, severity = SENSITIVE_FILENAMES[name_lower]
            findings.append(SecretFinding(
                file_path=item,
                relative_path=rel_path,
                reason=reason,
                severity=severity
            ))
            return
        
        # Check filename patterns
        for pattern, reason, severity in SENSITIVE_PATTERNS:
            if re.match(pattern, name_lower, re.IGNORECASE):
                findings.append(SecretFinding(
                    file_path=item,
                    relative_path=rel_path,
                    reason=reason,
                    severity=severity
                ))
                return  # Only report once per file
    
    scan_directory(project_path)
    
    # Sort by severity (high first)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 3), f.relative_path))
    
    return findings


def get_severity_emoji(severity: str) -> str:
    """Get an emoji indicator for severity level."""
    return {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }.get(severity, "⚪")


def format_findings_for_display(findings: list[SecretFinding]) -> str:
    """Format findings as a readable string for display."""
    if not findings:
        return "No sensitive files detected."
    
    lines = []
    for finding in findings:
        emoji = get_severity_emoji(finding.severity)
        lines.append(f"{emoji} {finding.relative_path}")
        lines.append(f"   {finding.reason}")
        lines.append("")
    
    return "\n".join(lines)

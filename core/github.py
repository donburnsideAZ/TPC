"""
GitHub authentication and operations for TPC.

Handles:
- Personal Access Token storage
- Credential injection for git operations
- Token validation
- Clone operations
"""

import json
import subprocess
import sys
import tempfile
import os
import stat
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def _subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = 0x08000000
    return kwargs


# TPC config location
TPC_CONFIG_DIR = Path.home() / ".tpc"
TPC_CONFIG_FILE = TPC_CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load the TPC config file."""
    if not TPC_CONFIG_FILE.exists():
        return {}
    
    try:
        with open(TPC_CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: dict) -> None:
    """Save the TPC config file."""
    TPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(TPC_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_github_token() -> Optional[str]:
    """Get the stored GitHub Personal Access Token."""
    config = load_config()
    return config.get("github_token")


def get_github_username() -> Optional[str]:
    """Get the stored GitHub username."""
    config = load_config()
    return config.get("github_username")


def save_github_credentials(username: str, token: str) -> None:
    """Save GitHub credentials to config."""
    config = load_config()
    config["github_username"] = username
    config["github_token"] = token
    save_config(config)


def clear_github_credentials() -> None:
    """Remove GitHub credentials from config."""
    config = load_config()
    config.pop("github_username", None)
    config.pop("github_token", None)
    save_config(config)


def has_github_credentials() -> bool:
    """Check if we have stored GitHub credentials."""
    return bool(get_github_token() and get_github_username())


def validate_token(username: str, token: str) -> tuple[bool, str]:
    """
    Validate a GitHub token by making a test API call.
    
    Returns (success, message).
    """
    try:
        # Use git ls-remote to test credentials
        # This is more reliable than API calls and tests actual git access
        result = subprocess.run(
            ["git", "ls-remote", f"https://{username}:{token}@github.com/{username}/{username}.git"],
            capture_output=True,
            text=True,
            timeout=15,
            **_subprocess_args()
        )
        
        # Even if repo doesn't exist, valid credentials won't give auth error
        # So let's use the API instead
        import urllib.request
        import urllib.error
        
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "TPC-App"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                actual_username = data.get("login", "")
                
                if actual_username.lower() != username.lower():
                    return True, f"Token valid! Note: GitHub username is '{actual_username}'"
                
                return True, f"Connected as {actual_username}"
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Invalid token. Please check and try again."
            elif e.code == 403:
                return False, "Token doesn't have required permissions."
            else:
                return False, f"GitHub error: {e.code}"
                
    except subprocess.TimeoutExpired:
        return False, "Connection timed out. Check your internet."
    except Exception as e:
        return False, f"Couldn't validate: {e}"


def run_git_with_auth(
    args: list[str],
    cwd: Path,
    timeout: int = 60
) -> subprocess.CompletedProcess:
    """
    Run a git command with GitHub authentication.
    
    Uses GIT_ASKPASS to provide credentials without embedding in URLs.
    """
    token = get_github_token()
    username = get_github_username()
    
    if not token or not username:
        # No credentials, run without auth (will likely fail for private repos)
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            **_subprocess_args()
        )
    
    # Create a temporary askpass script
    # This script will be called by git to get username and password
    askpass_script = None
    
    try:
        # Create temp script that returns credentials
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            askpass_script = f.name
            # Script checks if git is asking for username or password
            f.write(f'''#!/bin/bash
if [[ "$1" == *"Username"* ]]; then
    echo "{username}"
elif [[ "$1" == *"Password"* ]]; then
    echo "{token}"
fi
''')
        
        # Make it executable
        os.chmod(askpass_script, stat.S_IRWXU)
        
        # Set up environment with our askpass script
        env = os.environ.copy()
        env["GIT_ASKPASS"] = askpass_script
        env["GIT_TERMINAL_PROMPT"] = "0"  # Don't prompt in terminal
        
        # Run git with auth
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            **_subprocess_args()
        )
        
        return result
        
    finally:
        # Clean up the temp script
        if askpass_script and os.path.exists(askpass_script):
            os.unlink(askpass_script)


def clone_repository(
    url: str,
    destination: Path,
    progress_callback=None
) -> tuple[bool, str, Optional[Path]]:
    """
    Clone a GitHub repository.
    
    Args:
        url: GitHub repository URL (HTTPS)
        destination: Parent folder where repo will be cloned
        progress_callback: Optional callback for progress updates
    
    Returns (success, message, project_path or None).
    """
    # Parse the URL to get repo name
    repo_name = extract_repo_name(url)
    if not repo_name:
        return False, "Couldn't parse repository name from URL", None
    
    project_path = destination / repo_name
    
    if project_path.exists():
        return False, f"Folder '{repo_name}' already exists at this location", None
    
    token = get_github_token()
    username = get_github_username()
    
    if not token or not username:
        return False, "GitHub not connected. Go to Settings → GitHub to sign in.", None
    
    try:
        if progress_callback:
            progress_callback("Cloning repository...")
        
        # For clone, we need to embed creds in URL (askpass doesn't work as well for initial clone)
        # Parse and reconstruct URL with credentials
        auth_url = inject_credentials(url, username, token)
        
        result = subprocess.run(
            ["git", "clone", auth_url, str(project_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout for large repos
            **_subprocess_args()
        )
        
        if result.returncode != 0:
            error = result.stderr.strip()
            
            # Clean up failed clone
            if project_path.exists():
                import shutil
                shutil.rmtree(project_path)
            
            if "not found" in error.lower() or "404" in error:
                return False, "Repository not found. Check the URL and your access.", None
            elif "authentication" in error.lower() or "403" in error:
                return False, "Access denied. Check your token has 'repo' permission.", None
            else:
                return False, f"Clone failed: {error}", None
        
        # After clone, update remote to remove credentials from URL
        subprocess.run(
            ["git", "remote", "set-url", "origin", url],
            cwd=project_path,
            capture_output=True,
            **_subprocess_args()
        )
        
        return True, f"Cloned successfully!", project_path
        
    except subprocess.TimeoutExpired:
        # Clean up
        if project_path.exists():
            import shutil
            shutil.rmtree(project_path)
        return False, "Clone timed out. The repository might be very large.", None
    except Exception as e:
        return False, f"Error: {e}", None


def extract_repo_name(url: str) -> Optional[str]:
    """Extract repository name from a GitHub URL."""
    # Handle various GitHub URL formats:
    # https://github.com/user/repo
    # https://github.com/user/repo.git
    # git@github.com:user/repo.git
    
    url = url.strip().rstrip("/")
    
    if url.endswith(".git"):
        url = url[:-4]
    
    if "github.com" in url:
        # HTTPS format
        parts = url.split("/")
        if len(parts) >= 2:
            return parts[-1]
    
    if url.startswith("git@github.com:"):
        # SSH format
        path = url.replace("git@github.com:", "")
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[-1]
    
    return None


def inject_credentials(url: str, username: str, token: str) -> str:
    """Inject credentials into a GitHub HTTPS URL."""
    if not url.startswith("https://"):
        # Convert SSH to HTTPS if needed
        if url.startswith("git@github.com:"):
            path = url.replace("git@github.com:", "")
            url = f"https://github.com/{path}"
    
    # Parse and reconstruct with credentials
    parsed = urlparse(url)
    
    # Reconstruct: https://username:token@github.com/path
    auth_url = f"https://{username}:{token}@{parsed.netloc}{parsed.path}"
    
    if parsed.query:
        auth_url += f"?{parsed.query}"
    
    return auth_url


def normalize_github_url(url: str) -> str:
    """Convert any GitHub URL format to clean HTTPS format."""
    url = url.strip().rstrip("/")
    
    # SSH to HTTPS
    if url.startswith("git@github.com:"):
        path = url.replace("git@github.com:", "")
        url = f"https://github.com/{path}"
    
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    
    # Ensure https://
    if url.startswith("github.com"):
        url = f"https://{url}"
    
    return url


def fetch_user_repos(
    include_private: bool = True,
    sort_by: str = "updated"
) -> tuple[bool, str, list[dict]]:
    """
    Fetch the user's GitHub repositories.
    
    Args:
        include_private: Include private repos (requires repo scope)
        sort_by: Sort order - "updated", "created", "pushed", "full_name"
    
    Returns (success, message, list of repo dicts).
    
    Each repo dict contains:
        - name: str (repo name)
        - full_name: str (owner/repo)
        - clone_url: str (HTTPS clone URL)
        - private: bool
        - description: str or None
        - updated_at: str (ISO timestamp)
    """
    token = get_github_token()
    username = get_github_username()
    
    if not token or not username:
        return False, "Not connected to GitHub", []
    
    try:
        import urllib.request
        import urllib.error
        import json
        
        # Fetch repos - get up to 100, sorted by most recently updated
        url = f"https://api.github.com/user/repos?per_page=100&sort={sort_by}&direction=desc"
        
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "TPC-App"
            }
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            
            repos = []
            for repo in data:
                repos.append({
                    "name": repo.get("name", ""),
                    "full_name": repo.get("full_name", ""),
                    "clone_url": repo.get("clone_url", ""),
                    "private": repo.get("private", False),
                    "description": repo.get("description"),
                    "updated_at": repo.get("updated_at", ""),
                })
            
            return True, f"Found {len(repos)} repositories", repos
            
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Authentication failed. Check your token.", []
        elif e.code == 403:
            return False, "Access denied. Token may have expired.", []
        else:
            return False, f"GitHub error: {e.code}", []
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}", []
    except Exception as e:
        return False, f"Error: {e}", []

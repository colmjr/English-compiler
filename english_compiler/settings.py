"""Persistent settings for english-compiler.

Provides configuration file support so users don't need to specify
--frontend and --explain-errors on every command.

Config file location:
- Linux/macOS: ~/.config/english-compiler/config.toml
- Windows: Uses platformdirs if available, otherwise ~/english-compiler/config.toml

Config file format (TOML):
    [defaults]
    frontend = "claude"
    explain_errors = true
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    """User settings for english-compiler."""

    frontend: str | None = None
    explain_errors: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to a dictionary for serialization."""
        result: dict[str, Any] = {}
        if self.frontend is not None:
            result["frontend"] = self.frontend
        if self.explain_errors:
            result["explain_errors"] = self.explain_errors
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Create Settings from a dictionary."""
        return cls(
            frontend=data.get("frontend"),
            explain_errors=bool(data.get("explain_errors", False)),
        )


def get_config_path() -> Path:
    """Get the platform-appropriate config file path.

    Returns:
        Path to config.toml file (may not exist yet).
    """
    # Try platformdirs first (optional dependency)
    try:
        import platformdirs

        config_dir = Path(platformdirs.user_config_dir("english-compiler"))
    except ImportError:
        # Fall back to XDG-style on Unix, home directory on Windows
        if sys.platform == "win32":
            config_dir = Path.home() / "english-compiler"
        else:
            # Use XDG_CONFIG_HOME if set, otherwise ~/.config
            xdg_config = Path.home() / ".config"
            config_dir = xdg_config / "english-compiler"

    return config_dir / "config.toml"


def _parse_toml(text: str) -> dict[str, Any]:
    """Parse TOML text into a dictionary.

    Uses Python 3.11+ tomllib if available, otherwise falls back to
    simple manual parsing for basic key=value and [section] syntax.

    Args:
        text: TOML text to parse.

    Returns:
        Parsed dictionary.
    """
    # Try built-in tomllib (Python 3.11+)
    if sys.version_info >= (3, 11):
        import tomllib

        return tomllib.loads(text)

    # Simple fallback parser for basic TOML
    result: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None

    for line in text.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Section header
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            result[section_name] = {}
            current_section = result[section_name]
            continue

        # Key-value pair
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Parse value
            if value.lower() == "true":
                parsed_value: Any = True
            elif value.lower() == "false":
                parsed_value = False
            elif value.startswith('"') and value.endswith('"'):
                parsed_value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                parsed_value = value[1:-1]
            else:
                # Try to parse as number
                try:
                    parsed_value = int(value)
                except ValueError:
                    try:
                        parsed_value = float(value)
                    except ValueError:
                        parsed_value = value

            if current_section is not None:
                current_section[key] = parsed_value
            else:
                result[key] = parsed_value

    return result


def _generate_toml(settings: Settings) -> str:
    """Generate TOML text from Settings.

    Args:
        settings: Settings to serialize.

    Returns:
        TOML-formatted string.
    """
    lines = ["[defaults]"]
    data = settings.to_dict()

    for key, value in sorted(data.items()):
        # Convert key from snake_case (Python) to the config format
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")

    return "\n".join(lines) + "\n"


def load_settings() -> Settings:
    """Load settings from config file.

    Returns:
        Settings loaded from config file, or default Settings if file doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return Settings()

    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return Settings()

    try:
        data = _parse_toml(text)
    except Exception:
        return Settings()

    # Get the [defaults] section
    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        return Settings()

    return Settings.from_dict(defaults)


def save_settings(settings: Settings) -> bool:
    """Save settings to config file.

    Creates the config directory if it doesn't exist.

    Args:
        settings: Settings to save.

    Returns:
        True if successful, False on error.
    """
    config_path = get_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        text = _generate_toml(settings)
        config_path.write_text(text, encoding="utf-8")
        return True
    except OSError:
        return False


def delete_settings() -> bool:
    """Delete the config file.

    Returns:
        True if file was deleted or didn't exist, False on error.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return True

    try:
        config_path.unlink()
        return True
    except OSError:
        return False


# Valid values for settings
VALID_FRONTENDS = ("mock", "claude", "openai", "gemini", "qwen")

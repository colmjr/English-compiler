"""CLI config subcommand handlers."""

from __future__ import annotations

import argparse

from english_compiler.settings import (
    VALID_FRONTENDS,
    VALID_TARGETS,
    delete_settings,
    get_config_path,
    load_settings,
    save_settings,
)

TRUE_VALUE_STRINGS = ("true", "1", "yes", "on")
FALSE_VALUE_STRINGS = ("false", "0", "no", "off")


def parse_bool_setting(value: str) -> bool | None:
    normalized = value.lower()
    if normalized in TRUE_VALUE_STRINGS:
        return True
    if normalized in FALSE_VALUE_STRINGS:
        return False
    return None


def config_set(key: str, value: str) -> int:
    settings = load_settings()
    key_normalized = key.replace("-", "_")

    if key_normalized == "frontend":
        if value not in VALID_FRONTENDS:
            print(f"Invalid frontend: {value}")
            print(f"Valid options: {', '.join(VALID_FRONTENDS)}")
            return 1
        settings.frontend = value
    elif key_normalized == "explain_errors":
        parsed_bool = parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.explain_errors = parsed_bool
    elif key_normalized == "target":
        if value not in VALID_TARGETS:
            print(f"Invalid target: {value}")
            print(f"Valid options: {', '.join(VALID_TARGETS)}")
            return 1
        settings.target = value
    elif key_normalized == "regen":
        parsed_bool = parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.regen = parsed_bool
    elif key_normalized == "freeze":
        parsed_bool = parse_bool_setting(value)
        if parsed_bool is None:
            print(f"Invalid boolean value: {value}")
            print("Use: true, false, 1, 0, yes, no, on, off")
            return 1
        settings.freeze = parsed_bool
    else:
        print(f"Unknown setting: {key}")
        print("Valid settings: frontend, target, explain-errors, regen, freeze")
        return 1

    if not save_settings(settings):
        print(f"Failed to write config file: {get_config_path()}")
        return 1

    print(f"Set {key} = {value}")
    return 0


def config_get(key: str) -> int:
    settings = load_settings()
    key_normalized = key.replace("-", "_")

    if key_normalized == "frontend":
        value = settings.frontend if settings.frontend else "(not set)"
    elif key_normalized == "explain_errors":
        value = str(settings.explain_errors).lower()
    elif key_normalized == "target":
        value = settings.target if settings.target else "(not set)"
    elif key_normalized == "regen":
        value = str(settings.regen).lower()
    elif key_normalized == "freeze":
        value = str(settings.freeze).lower()
    else:
        print(f"Unknown setting: {key}")
        print("Valid settings: frontend, target, explain-errors, regen, freeze")
        return 1

    print(f"{key}: {value}")
    return 0


def config_list() -> int:
    settings = load_settings()

    print("Current settings:")
    print(f"  frontend: {settings.frontend if settings.frontend else '(not set)'}")
    print(f"  target: {settings.target if settings.target else '(not set)'}")
    print(f"  explain-errors: {str(settings.explain_errors).lower()}")
    print(f"  regen: {str(settings.regen).lower()}")
    print(f"  freeze: {str(settings.freeze).lower()}")

    config_path = get_config_path()
    if config_path.exists():
        print(f"\nConfig file: {config_path}")
    else:
        print(f"\nConfig file: {config_path} (not created yet)")

    return 0


def config_path() -> int:
    print(get_config_path())
    return 0


def config_reset() -> int:
    path = get_config_path()
    if not path.exists():
        print(f"Config file does not exist: {path}")
        return 0

    if not delete_settings():
        print(f"Failed to delete config file: {path}")
        return 1

    print(f"Deleted config file: {path}")
    return 0


def config_command(args: argparse.Namespace) -> int:
    config_action = getattr(args, "config_action", None)

    if config_action == "set":
        return config_set(args.key, args.value)
    if config_action == "get":
        return config_get(args.key)
    if config_action == "list":
        return config_list()
    if config_action == "path":
        return config_path()
    if config_action == "reset":
        return config_reset()

    print("Usage: english-compiler config {set,get,list,path,reset}")
    return 1


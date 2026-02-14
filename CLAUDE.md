# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Specs

See `docs/` for project specifications. Read these before implementing features.

## Development Environment

Python 3.14 project using uv for package management. Dependencies are provided via Nix:

```bash
nix-shell        # Enter dev shell (provides python 3.14 + uv)
```

`UV_PYTHON_PREFERENCE=only-system` is set in the shell hook so uv uses the Nix-provided Python rather than downloading its own.

## Code Style

- Use type hints on all function signatures (parameters and return types).
- Follow PEP 8. Use ruff for linting and formatting.
- All new code must have corresponding tests.

## Commands

```bash
uv run main.py        # Run the project
uv add <package>      # Add a dependency
uv sync               # Install/sync dependencies from lockfile
```

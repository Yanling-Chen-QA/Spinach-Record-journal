## Environment Management with uv

This repository uses `uv` as the source of truth for dependency management.

- Base dependencies are defined in `pyproject.toml` under `[project.dependencies]`.
- CoreClaw-only dependencies are defined under `[project.optional-dependencies].coreclaw`.

### Install base dependencies

```bash
uv sync
```

### Install base + CoreClaw dependencies

```bash
uv sync --extra coreclaw
```

### Run CoreClaw

```bash
uv run --extra coreclaw python 11_CoreClaw/Claw.py
```

### Export `11_CoreClaw/requirements.txt`

Use this only for compatibility with tools that still require `requirements.txt`.

```bash
uv export --extra coreclaw -o 11_CoreClaw/requirements.txt
```

If you want hashes in the exported file:

```bash
uv export --extra coreclaw --generate-hashes -o 11_CoreClaw/requirements.txt
```


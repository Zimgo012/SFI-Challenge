"""Provision shared service authentication, then replace this process with Uvicorn."""

import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile


def validate_token(token):
    if len(token) < 32 or not token.isascii() or any(char.isspace() for char in token):
        raise ValueError("Autopilot tokens must contain at least 32 ASCII characters without whitespace")
    return token


def saved_token(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Publish a complete file atomically if services start concurrently.
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".autopilot-")
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(secrets.token_urlsafe(48))
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            os.unlink(temporary)
    return validate_token(path.read_text())


def configure_auth(environment):
    token_file = environment.get("SFI_AUTOPILOT_TOKEN_FILE")
    if not token_file:
        return
    backend = environment.get("MODEL_AUTOPILOT_LIVE_TOKEN", "")
    model = environment.get("SFI_AUTOPILOT_LIVE_TOKEN", "")
    if backend and model and backend != model:
        raise ValueError("Backend and model autopilot tokens must match")
    token = validate_token(backend or model) if backend or model else saved_token(Path(token_file))
    environment["MODEL_AUTOPILOT_LIVE_TOKEN"] = token
    environment["SFI_AUTOPILOT_LIVE_TOKEN"] = token


def write_service_env(environment):
    """Persist this process's resolved configuration for dotenv-aware services."""
    configured_path = environment.get("SFI_SERVICE_ENV_FILE")
    if not configured_path:
        return
    path = Path(configured_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".service-env-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            for key, value in sorted(environment.items()):
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                    stream.write(f"{key}={json.dumps(value, ensure_ascii=False)}\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    try:
        configure_auth(os.environ)
        write_service_env(os.environ)
        if len(sys.argv) < 2:
            raise ValueError("A service command is required")
    except (ValueError, OSError) as error:
        print(f"Service configuration failed: {error}", file=sys.stderr)
        sys.exit(1)
    os.execvp(sys.argv[1], sys.argv[1:])

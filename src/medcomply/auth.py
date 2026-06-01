from pathlib import Path
from typing import Optional

import yaml

ROLE_DOC_CLASSES: dict[str, list[str]] = {
    "admin": ["hipaa", "osha", "infection_control", "medical_waste", "general"],
    "manager": ["hipaa", "osha", "infection_control", "general"],
    "staff": ["general", "infection_control"],
}

_CONFIG_PATH = Path("config/auth.yaml")


def load_authenticator():
    import streamlit_authenticator as stauth

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Auth config not found at {_CONFIG_PATH}. "
            "Run scripts/create_auth_config.py to generate it."
        )
    with open(_CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    return stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )


def get_current_user(
    auth_status: Optional[bool], username: str
) -> Optional[tuple[str, str]]:
    """Return (user_id, role) from verified session, or None if not authenticated."""
    if not auth_status:
        return None

    config_path = _CONFIG_PATH
    if not config_path.exists():
        return None

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    user_data = cfg.get("credentials", {}).get("usernames", {}).get(username)
    if user_data is None:
        return None

    role = user_data.get("role", "staff")
    return (username, role)

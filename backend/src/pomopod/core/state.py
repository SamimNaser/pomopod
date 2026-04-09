from pathlib import Path

from pomopod.core import config
from pomopod.core.constants import DEFAULT_ACTIVE_SPACE
from pomopod.core.models import Space

STATE_DIR = Path.home() / ".local" / "share" / "pomopod"
ACTIVE_SPACE_FILE = STATE_DIR / "active_space"


def _ensure_state_dir() -> None:
  STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_active_space_name() -> str | None:
  _ensure_state_dir()

  if not ACTIVE_SPACE_FILE.exists():
    prof = set_active_space(DEFAULT_ACTIVE_SPACE)
    if not prof:
      return None
    return DEFAULT_ACTIVE_SPACE

  return ACTIVE_SPACE_FILE.read_text().strip()


def set_active_space(name: str) -> Space | None:
  _ensure_state_dir()
  spaces = config.get_spaces()

  if name not in spaces.keys():
    return None

  ACTIVE_SPACE_FILE.write_text(name)
  return spaces.get(name)

from pathlib import Path

from pomopod.core import config
from pomopod.core.models import Space
from pomopod.err.config import SpaceDoesNotExist
from pomopod.err.state import ActiveSpaceNotSet

STATE_DIR = Path.home() / ".local" / "share" / "pomopod"
ACTIVE_SPACE_FILE = STATE_DIR / "active_space"


def _ensure_state_dir() -> None:
  STATE_DIR.mkdir(parents=True, exist_ok=True)


def _is_active_space_set() -> bool:
  return ACTIVE_SPACE_FILE.exists()


def get_active_space_name() -> str:
  """
  Get the name of the active space.
  Raises `ActiveSpaceNotSet` if active the space does not exist.
  """
  _ensure_state_dir()

  if not ACTIVE_SPACE_FILE.exists():
    raise ActiveSpaceNotSet

  return ACTIVE_SPACE_FILE.read_text().strip()


def set_active_space(space_name: str) -> Space:
  """
  Set the active space.
  Raises `SpaceDoesNotExist` if the space does not exist.
  """
  _ensure_state_dir()
  spaces = config.get_spaces()

  if space_name not in spaces.keys():
    raise SpaceDoesNotExist

  ACTIVE_SPACE_FILE.write_text(space_name)
  return spaces[space_name]

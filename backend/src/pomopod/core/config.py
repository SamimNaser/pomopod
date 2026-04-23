import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from pomopod.core import state
from pomopod.core.models import Config, DaemonSettings, NotificationSettings, Space
from pomopod.err.config import SpaceAlreadyExists, SpaceDoesNotExist

CONFIG_DIR = Path.home() / ".config" / "pomopod"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir() -> None:
  CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def is_config_correct() -> bool:
  try:
    _load_config()
  except ValidationError:
    return False
  return True


def _get_default_config() -> Config:
  return Config()


def _load_config() -> Config:
  """
  Load and return the config file.
  Raises `ValidationError` if the config file is invalid.
  """
  if not CONFIG_FILE.exists():
    _ensure_config_dir()
    config = _get_default_config()
    _save_config(config)
    return config

  with open(CONFIG_FILE, "r") as f:
    config_json = json.load(f)

  try:
    config = Config.model_validate(config_json)
  except ValidationError:
    raise ValidationError

  return config


def _save_config(config: Config) -> None:
  _ensure_config_dir()
  with open(CONFIG_FILE, "w") as f:
    json.dump(config.model_dump(), f, indent=2)


def get_spaces() -> dict[str, Space]:
  config = _load_config()
  return config.spaces


def get_space(name: str) -> Space:
  """
  Get a space from the config.
  Raises `SpaceDoesNotExist` if the space does not exist.
  """
  config = _load_config()

  if name not in list(config.spaces.keys()):
    raise SpaceDoesNotExist

  return config.spaces[name]


def get_space_names() -> list[str]:
  config = _load_config()
  return list(config.spaces.keys())


def get_active_space() -> Space:
  config = _load_config()

  active_space_name = state.get_active_space_name()

  return config.spaces[active_space_name]


def add_space(name: str, space: Space) -> Space:
  """
  Add a space to the config.
  Raises `SpaceAlreadyExists` if the space already exists.
  """
  config = _load_config()

  if name in list(config.spaces.keys()):
    raise SpaceAlreadyExists

  config.spaces[name] = space
  _save_config(config)
  return space


def edit_space(name: str, updates: dict) -> Space:
  """
  Add a space to the config.
  Raises `SpaceDoesNotExist` if the space does not exist.
  And raises `SpaceAlreadyExist` if the space already exists.
  """
  config = _load_config()

  spaces = list(config.spaces.keys())
  if name not in spaces:
    raise SpaceDoesNotExist
  if updates["name"] in spaces:
    raise SpaceAlreadyExists

  current = config.spaces[name]
  updated_data = current.model_dump()
  updated_data.update(updates)

  config.spaces[name] = Space(**updated_data)
  _save_config(config)
  return config.spaces[name]


def remove_space(name: str) -> Space:
  """
  Remove a space from the config.
  Raises `SpaceDoesNotExist` if the space does not exist.
  """
  config = _load_config()

  if name not in list(config.spaces.keys()):
    raise SpaceDoesNotExist

  space = config.spaces.pop(name)
  _save_config(config)
  return space


def get_daemon_settings() -> DaemonSettings:
  config = _load_config()
  return config.daemon


def update_daemon_settings(
  host: Optional[str] = None, port: Optional[int] = None
) -> DaemonSettings:
  """
  Update the daemon settings.
  Raises `ValidationError` if the settings are invalid.
  """

  if not host and not port:
    raise ValidationError

  config = _load_config()
  if not host:
    host = config.daemon.host
  if not port:
    port = config.daemon.port

  try:
    config.daemon = DaemonSettings.model_validate({"host": host, "port": port})
  except ValidationError:
    raise ValidationError

  _save_config(config)
  return config.daemon


def get_notification_settings() -> NotificationSettings:
  config = _load_config()
  return config.notifications


def update_notification_settings(enabled: bool) -> NotificationSettings:
  config = _load_config()
  config.notifications = NotificationSettings(enabled=enabled)
  _save_config(config)
  return config.notifications

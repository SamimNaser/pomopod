import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from pomopod.core import state
from pomopod.core.models import Config, DaemonSettings, NotificationSettings, Space

CONFIG_DIR = Path.home() / ".config" / "pomopod"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir() -> None:
  CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _get_default_config() -> Config:
  return Config()


def _load_config() -> Config:
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
    return _get_default_config()

  return config


def _save_config(config: Config) -> None:
  _ensure_config_dir()
  with open(CONFIG_FILE, "w") as f:
    json.dump(config.model_dump(), f, indent=2)


def get_spaces() -> dict[str, Space]:
  config = _load_config()
  return config.spaces


def get_space_names() -> list[str]:
  config = _load_config()
  return list(config.spaces.keys())


def get_active_space() -> Space | None:
  config = _load_config()

  active_space_name = state.get_active_space_name()
  if active_space_name is None:
    return None

  return config.spaces.get(active_space_name)


def add_space(name: str, space: Space) -> Space | None:
  config = _load_config()

  if name in list(config.spaces.keys()):
    return None

  config.spaces[name] = space
  _save_config(config)
  return space


def edit_space(name: str, updates: dict) -> Space | None:
  config = _load_config()

  if name not in list(config.spaces.keys()):
    return None

  current = config.spaces[name]
  updated_data = current.model_dump()
  updated_data.update(updates)

  config.spaces[name] = Space(**updated_data)
  _save_config(config)
  return config.spaces[name]


def remove_space(name: str) -> Space | None:
  config = _load_config()

  if name not in list(config.spaces.keys()):
    return None

  space = config.spaces.pop(name)
  _save_config(config)
  return space


def get_daemon_settings() -> DaemonSettings:
  config = _load_config()
  return config.daemon


def update_daemon_settings(
  host: Optional[str] = None, port: Optional[int] = None
) -> DaemonSettings:
  config = _load_config()
  if not host:
    host = config.daemon.host
  if not port:
    port = config.daemon.port

  config.daemon = DaemonSettings.model_validate({"host": host, "port": port})
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

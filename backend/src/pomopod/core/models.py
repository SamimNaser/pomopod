from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from pomopod.core.constants import DEFAULT_ACTIVE_SPACE


class CatppuccinColor(str, Enum):
  ROSEWATER = "rosewater"
  FLAMINGO = "flamingo"
  PINK = "pink"
  MAUVE = "mauve"
  RED = "red"
  MAROON = "maroon"
  PEACH = "peach"
  YELLOW = "yellow"
  GREEN = "green"
  TEAL = "teal"
  SKY = "sky"
  SAPPHIRE = "sapphire"
  BLUE = "blue"
  LAVENDER = "lavender"


def validate_color(v: str) -> str:
  v = v.lower().strip()

  if v in CatppuccinColor.__members__.values():
    return v

  if v.startswith("#"):
    hex = v[1:]
    if len(hex) in (3, 6) and all(c in "0123456789abcdef" for c in hex):
      return v

  raise ValueError(f"Invalid color: {v}. Use Catppuccin colors or #RRGGBB")


ValidatedColor = Annotated[str, BeforeValidator(validate_color)]


class Space(BaseModel):
  focus_duration: int = Field(default=25, ge=1, le=600, description="Focus duration in minutes")
  short_break_duration: int = Field(default=5, ge=1, le=120, description="Short break in minutes")
  long_break_duration: int = Field(default=10, ge=1, le=300, description="Long break in minutes")

  sessions_until_long_break: int = Field(
    default=4, ge=1, le=25, description="Sessions until long break"
  )

  color: ValidatedColor = Field(default=CatppuccinColor.ROSEWATER, description="Color")

  model_config = {
    "str_strip_whitespace": True,
  }


class DaemonSettings(BaseModel):
  host: str = Field(default="127.0.0.1", description="Host")
  port: int = Field(default=8765, description="Port")


class NotificationSettings(BaseModel):
  enabled: bool = Field(default=True, description="Enable notifications")


class Config(BaseModel):
  spaces: dict[str, Space] = Field(
    default_factory=lambda: {DEFAULT_ACTIVE_SPACE: Space()},
    description="Spaces",
  )
  daemon: DaemonSettings = Field(default_factory=DaemonSettings, description="Daemon settings")
  notifications: NotificationSettings = Field(
    default_factory=NotificationSettings, description="Notification settings"
  )


class TimerStateType(str, Enum):
  FOCUS = "FOCUS"
  SHORT_BREAK = "SHORT_BREAK"
  LONG_BREAK = "LONG_BREAK"
  IDLE = "IDLE"


class TimerState(BaseModel):
  space_name: str = DEFAULT_ACTIVE_SPACE
  current_type: TimerStateType = TimerStateType.IDLE
  current_session_number: int = 1
  sessions_until_long_break: int = 4
  is_paused: bool = True
  end_timestamp_ms: int = 0
  base_color: str = "lavender"

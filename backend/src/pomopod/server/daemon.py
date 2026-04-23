from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Path, Query
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel, ValidationError
from scalar_fastapi import get_scalar_api_reference

from pomopod.core import config
from pomopod.core import state as state_core
from pomopod.core.models import DaemonSettings, NotificationSettings, Space, TimerState
from pomopod.err.config import SpaceAlreadyExists, SpaceDoesNotExist
from pomopod.err.state import ActiveSpaceNotSet
from pomopod.server import notifications as notif
from pomopod.server import state as state_server
from pomopod.server.timer import TimerManager

timer_state = TimerState()
timer_manager = TimerManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
  global timer_state

  saved = state_server.load_timer_state()
  if saved is not None:
    timer_state = saved

  space = config.get_active_space()
  timer_manager.start(_tick_callback, space, timer_state)

  yield

  timer_manager.stop()
  state_server.save_timer_state(timer_state)
  state_server.clear_daemon_pid()


app = FastAPI(
  title="Pomopod Daemon API",
  description=(
    "HTTP API for the Pomopod pomodoro timer daemon. "
    "Manages active timer state, pomodoro spaces, and daemon configuration. "
    "Designed for use by CLI, TUI, and GUI clients via HTTP requests to localhost:8765."
  ),
  version="0.1.0",
  lifespan=lifespan,
  openapi_tags=[
    {
      "name": "Root",
      "description": "Root endpoint for basic API availability and health checks",
    },
    {
      "name": "Timer",
      "description": "Endpoints for controlling and querying the active pomodoro timer state, including start, pause, resume, stop, and reset operations",
    },
    {
      "name": "Space",
      "description": "Endpoints for managing pomodoro spaces: create, edit, delete, rename, and switch between different spaces",
    },
    {
      "name": "Config",
      "description": "Endpoints for querying and updating daemon runtime settings and notification preferences",
    },
  ],
)


def _tick_callback(space: Space):
  """Called periodically to check and cycle timer."""
  if timer_state.is_paused:
    return

  if timer_state.get_remaining_time_ms() > 0:
    return

  timer_state.cycle_session(space)
  notif.notify_session_start(timer_state.current_type.value)
  state_server.save_timer_state(timer_state)


def _require_active_space() -> tuple[str, Space]:
  space_name = state_core.get_active_space_name()
  space = config.get_active_space()

  if not space or not space_name:
    raise HTTPException(status_code=404, detail="No active space")

  return space_name, space


class Health(BaseModel):
  status: str


@app.get(
  "/",
  tags=["Root"],
  summary="Health check",
  description="Basic endpoint to verify the Pomopod daemon is running and responsive.",
  response_model=Health,
)
async def root() -> Health:
  return Health(status="OK")


@app.get(
  "/scalar",
  include_in_schema=False,
  summary="Scalar API documentation",
  description="Serves the Scalar interactive API documentation interface for exploring and testing endpoints.",
)
async def scalar_html():
  return get_scalar_api_reference(
    openapi_url=app.openapi_url,
  )


@app.get(
  "/status",
  tags=["Timer"],
  response_model=TimerState,
  summary="Get current timer state",
  description="Returns the full state of the active pomodoro timer. Automatically calculates the remaining time before returning. Includes session type, pause status, cycle count, and associated space name.",
  response_description="Complete timer state object with current session details",
  responses={422: {"description": "Validation error"}},
)
async def status() -> TimerState:
  timer_state.get_remaining_time_ms()
  return timer_state


@app.post(
  "/start",
  tags=["Timer"],
  response_model=TimerState,
  summary="Start the pomodoro timer",
  description="Starts the active pomodoro timer for the current space. If the timer was paused, it resumes; otherwise, it starts a new FOCUS session based on the space's configuration. Sends a session start notification and persists timer state to disk.",
  response_description="Updated timer state after starting",
  responses={
    404: {"description": "No active space set"},
    422: {"description": "Validation error"},
  },
)
async def start():
  try:
    space_name, space = _require_active_space()
    timer_state.start(space_name, space)
    notif.notify_session_start(timer_state.current_type.value)
    state_server.save_timer_state(timer_state)
    return timer_state

  except ActiveSpaceNotSet:
    raise HTTPException(404, "No active space set")


@app.post(
  "/pause-resume",
  tags=["Timer"],
  response_model=TimerState,
  summary="Toggle pause/resume timer",
  description="Toggles the timer between paused and running states. If currently paused, resumes the timer; if running, pauses it. Sends a pause/resume notification and persists timer state to disk.",
  response_description="Updated timer state after toggling pause/resume",
  responses={422: {"description": "Validation error"}},
)
async def pause_resume():
  if timer_state.is_paused:
    timer_state.resume()
  else:
    timer_state.pause()

  notif.notify_session_pause_resume(timer_state.current_type.value, paused=timer_state.is_paused)
  state_server.save_timer_state(timer_state)
  return timer_state


@app.post(
  "/pause",
  tags=["Timer"],
  response_model=TimerState,
  summary="Pause the timer",
  description="Pauses the active pomodoro timer if it is currently running. Sends a pause notification and persists timer state to disk.",
  response_description="Updated timer state after pausing",
  responses={422: {"description": "Validation error"}},
)
async def pause():
  timer_state.pause()

  notif.notify_session_pause_resume(timer_state.current_type.value, paused=timer_state.is_paused)
  state_server.save_timer_state(timer_state)
  return timer_state


@app.post(
  "/resume",
  tags=["Timer"],
  response_model=TimerState,
  summary="Resume the timer",
  description="Resumes the active pomodoro timer if it is currently paused. Sends a resume notification and persists timer state to disk.",
  response_description="Updated timer state after resuming",
  responses={422: {"description": "Validation error"}},
)
async def resume():
  timer_state.resume()

  notif.notify_session_pause_resume(timer_state.current_type.value, paused=timer_state.is_paused)
  state_server.save_timer_state(timer_state)
  return timer_state


@app.post(
  "/reset-time",
  tags=["Timer"],
  response_model=TimerState,
  summary="Reset timer to full session duration",
  description="Resets the timer's remaining time to the full duration of the current session type (FOCUS/SHORT_BREAK/LONG_BREAK) based on the active space's configuration. Persists timer state to disk.",
  response_description="Updated timer state after resetting time",
  responses={
    404: {"description": "No active space set"},
    422: {"description": "Validation error"},
  },
)
async def reset():
  try:
    _, space = _require_active_space()
    timer_state.reset_time(space)
    state_server.save_timer_state(timer_state)
    return timer_state

  except ActiveSpaceNotSet:
    raise HTTPException(404, "No active space set")


@app.post(
  "/reset-count",
  tags=["Timer"],
  response_model=TimerState,
  summary="Reset session cycle count",
  description="Resets the pomodoro cycle count to 1 for the active timer. Persists timer state to disk.",
  response_description="Updated timer state after resetting cycle count",
  responses={422: {"description": "Validation error"}},
)
async def reset_count():
  timer_state.reset_count()
  state_server.save_timer_state(timer_state)
  return timer_state


@app.post(
  "/stop",
  tags=["Timer"],
  response_model=TimerState,
  summary="Stop the timer",
  description="Stops the active pomodoro timer, resetting its state to IDLE. Sends a session stop notification and persists timer state to disk.",
  response_description="Updated timer state after stopping",
  responses={422: {"description": "Validation error"}},
)
async def stop():
  timer_state.stop()
  notif.notify_session_stop()
  state_server.save_timer_state(timer_state)
  return timer_state


@app.get(
  "/spaces/active",
  tags=["Space"],
  response_model=Space,
  summary="Get active space details",
  description="Returns the full configuration of the currently active pomodoro space.",
  response_description="Active space configuration object",
  responses={
    404: {"description": "No active space set"},
    422: {"description": "Validation error"},
  },
)
async def get_active_space():
  try:
    space = config.get_active_space()
    return space
  except ActiveSpaceNotSet:
    raise HTTPException(404, "No active space")


@app.get(
  "/spaces/active/name",
  tags=["Space"],
  response_model=str,
  summary="Get active space name",
  description="Returns the name of the currently active pomodoro space.",
  response_description="Name of the active space as a string",
  responses={
    404: {"description": "No active space set"},
    422: {"description": "Validation error"},
  },
)
async def get_active_space_name():
  try:
    space_name = state_core.get_active_space_name()
    return space_name
  except ActiveSpaceNotSet:
    raise HTTPException(404, "No active space")


@app.post(
  "/spaces/active/{space_name}",
  tags=["Space"],
  response_model=Space,
  summary="Switch to specified space",
  description="Sets the specified space as the currently active pomodoro space and resets the timer duration. Returns the space configuration.",
  response_description="Space configuration of switched-to active space",
  responses={
    404: {"description": "Space does not exist"},
    422: {"description": "Validation error"},
  },
)
async def set_active_space(
  space_name: str = Path(..., description="Name of the space to set as active"),
):
  try:
    space = state_core.set_active_space(space_name)
    timer_manager.change_space(space)
    timer_state.reset_time(space)
    return space
  except SpaceDoesNotExist:
    raise HTTPException(404, "Space does not exist")


@app.get(
  "/spaces/list",
  tags=["Space"],
  response_model=dict[str, Space],
  summary="List all spaces",
  description="Returns a dictionary of all configured pomodoro spaces, keyed by their unique names.",
  response_description="Dictionary mapping space names to their full configuration objects",
  responses={422: {"description": "Validation error"}},
)
async def list_spaces():
  spaces = config.get_spaces()
  return spaces


@app.get(
  "/spaces/list-names",
  tags=["Space"],
  response_model=list[str],
  summary="List all space names",
  description="Returns a list of the names of all configured pomodoro spaces.",
  response_description="List of space name strings",
  responses={422: {"description": "Validation error"}},
)
async def list_space_names():
  spaces = config.get_space_names()
  return spaces


@app.get(
  "/spaces/{space_name}",
  tags=["Space"],
  response_model=Space,
  summary="Get space details",
  description="Returns the configuration of the specified pomodoro space.",
  response_description="Space configuration object",
  responses={
    404: {"description": "Space does not exist"},
    422: {"description": "Validation error"},
  },
)
async def get_space(space_name: str = Path(..., description="Name of the space to retrieve")):
  try:
    space = config.get_space(space_name)
    return space

  except SpaceDoesNotExist:
    raise HTTPException(404, "Space does not exist")


@app.post(
  "/spaces",
  tags=["Space"],
  response_model=Space,
  summary="Create new space",
  description="Adds a new pomodoro space with the provided configuration. Switches the timer to use the new space and resets the timer duration. Returns the new space configuration.",
  response_description="Newly created space configuration object",
  responses={
    409: {"description": "Space already exists"},
    422: {"description": "Validation error"},
  },
)
async def add_space(space: Space = Body(..., description="Space configuration object to create")):
  try:
    new_space = config.add_space(space.name, space)
    timer_manager.change_space(new_space)
    timer_state.reset_time(new_space)
    return new_space

  except SpaceAlreadyExists:
    raise HTTPException(409, "Space already exists")


@app.patch(
  "/spaces/{space_name}",
  tags=["Space"],
  response_model=Space,
  summary="Edit existing space",
  description="Updates the configuration of the specified space with the provided fields. If the edited space is the active space, switches the timer to use the updated configuration and resets the timer duration. Returns the updated space configuration.",
  response_description="Updated space configuration object",
  responses={
    404: {"description": "Space does not exist"},
    409: {"description": "New space name already exists"},
    422: {"description": "Validation error"},
  },
)
async def edit_space(
  space_name: str = Path(..., description="Name of the space to edit"),
  space: Space = Body(..., description="Updated space configuration fields"),
):
  try:
    edited_space = config.edit_space(space_name, space.model_dump())
    if space_name == timer_state.space_name:
      timer_manager.change_space(edited_space)
      timer_state.reset_time(edited_space)
    return edited_space

  except SpaceDoesNotExist:
    raise HTTPException(404, "Space does not exist")
  except SpaceAlreadyExists:
    raise HTTPException(409, "New space name already exists")


@app.delete(
  "/spaces/{space_name}",
  tags=["Space"],
  response_model=Space,
  summary="Delete space",
  description="Removes the specified space from the configuration. Cannot remove the active space. Returns the deleted space configuration.",
  response_description="Deleted space configuration object",
  responses={
    404: {"description": "Space does not exist or cannot remove active space"},
    422: {"description": "Validation error"},
  },
)
async def remove_space(space_name: str = Path(..., description="Name of the space to delete")):
  try:
    if space_name == timer_state.space_name:
      raise HTTPException(404, "Cant remove active space")
    removed_space = config.remove_space(space_name)
    return removed_space

  except SpaceDoesNotExist:
    raise HTTPException(404, "Space does not exist")


@app.patch(
  "/spaces/rename/{space_name}",
  tags=["Space"],
  response_model=Space,
  summary="Rename space",
  description="Renames the specified space to a new name. Removes the old space, creates a new one with the updated name, and switches the timer to use the renamed space. Sends a session stop notification. Returns the renamed space configuration.",
  response_description="Renamed space configuration object",
  responses={
    404: {"description": "Space does not exist"},
    409: {"description": "New space name already exists"},
    422: {"description": "Validation error"},
  },
)
async def rename_space(
  space_name: str = Path(..., description="Current name of the space to rename"),
  new_name: str = Query(..., description="New name for the space"),
):
  try:
    space_names = config.get_space_names()
    if new_name in space_names:
      raise HTTPException(409, "New space name already exists")

    space = config.remove_space(space_name)
    space.name = new_name
    config.add_space(new_name, space)
    timer_manager.change_space(space)
    notif.notify_session_stop()
    return space

  except SpaceDoesNotExist:
    raise HTTPException(404, "Space does not exist")
  except SpaceAlreadyExists:
    raise HTTPException(409, "New space name already exists")


@app.get(
  "/config/daemon",
  tags=["Config"],
  response_model=DaemonSettings,
  summary="Get daemon settings",
  description="Returns the current daemon configuration, including host and port settings for the HTTP server.",
  response_description="Daemon settings object with host and port",
  responses={422: {"description": "Validation error"}},
)
async def get_daemon_settings():
  daemon_settings = config.get_daemon_settings()
  return daemon_settings


@app.get(
  "/config/notif",
  tags=["Config"],
  response_model=NotificationSettings,
  summary="Get notification settings",
  description="Returns the current notification configuration, indicating whether desktop notifications are enabled.",
  response_description="Notification settings object with enable status",
  responses={422: {"description": "Validation error"}},
)
async def get_notification_settings():
  notification_settings = config.get_notification_settings()
  return notification_settings


@app.post(
  "/config/daemon",
  tags=["Config"],
  response_model=DaemonSettings,
  summary="Update daemon settings",
  description="Updates the daemon's host and/or port settings. Unspecified parameters are left unchanged.",
  response_description="Updated daemon settings object",
  responses={
    404: {"description": "Invalid daemon settings"},
    422: {"description": "Validation error"},
  },
)
async def update_daemon_settings(
  host: Optional[str] = Query(None, description="New daemon host"),
  port: Optional[int] = Query(None, description="New daemon port"),
):
  try:
    config.update_daemon_settings(host, port)
  except ValidationError:
    raise HTTPException(404, "Invalid daemon settings")

  daemon_settings = config.get_daemon_settings()
  return daemon_settings


@app.post(
  "/config/notif",
  tags=["Config"],
  response_model=NotificationSettings,
  summary="Toggle notification settings",
  description="Enables or disables desktop notifications for the daemon. Returns the updated notification settings.",
  response_description="Updated notification settings object",
  responses={422: {"description": "Validation error"}},
)
async def update_notification_settings(
  enable: bool = Query(..., description="Enable (true) or disable (false) notifications"),
):
  notification_settings = config.update_notification_settings(enable)
  return notification_settings

from typing import Optional

import typer
from pydantic import ValidationError
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pomopod.core import config, state
from pomopod.core.models import Space

app = typer.Typer()
console = Console()


def complete_spaces(incomplete: str) -> list[str]:
  return [p for p in config.get_space_names() if p.startswith(incomplete)]


@app.command(name="ls")
def list_spaces():
  """List all pomodoro spaces with details."""
  spaces = config.get_spaces()

  headers = ("Name", "Focus", "Short Break", "Long Break", "Sessions", "Color")
  table = Table(*headers, title="Spaces")

  for name, space in spaces.items():
    table.add_row(
      name,
      str(space.focus_duration),
      str(space.short_break_duration),
      str(space.long_break_duration),
      str(space.sessions_before_long_break),
      str(space.color),
    )

  console.print(table)


def _print_space(name: str, space: Space):
  """Print the pomodoro space details."""
  table = Table(title=f"{name}")
  table.add_column("Setting", style="cyan")
  table.add_column("Value", style="green")

  table.add_row("Focus", str(space.focus_duration))
  table.add_row("Short Break", str(space.short_break_duration))
  table.add_row("Long Break", str(space.long_break_duration))
  table.add_row("Sessoins", str(space.sessions_before_long_break))
  table.add_row("Color", space.color)

  console.print(table)


@app.command(name="show")
def show_active_space():
  """Show the active pomodoro space details."""
  name = state.get_active_space_name()
  space = config.get_active_space()

  if space is None or name is None:
    rprint("No active space")
    return

  _print_space(name, space)


@app.command(name="get")
def show_space(
  name: str = typer.Argument(
    ...,
    help="Name of the pomodoro space",
  ),
):
  """Show the pomodoro space details."""
  space = config.get_spaces().get(name)

  if space is None:
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
    return

  _print_space(name, space)


@app.command(name="set")
def set_space(
  name: str = typer.Argument(
    ...,
    help="Name of the pomodoro space",
    autocompletion=complete_spaces,
  ),
):
  """Set the active pomodoro space."""
  space = state.set_active_space(name)
  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
  else:
    rprint(f'Active space set to [bold green]"{name}"[/bold green]')


def _validate_space(space_dict: dict) -> Space:
  try:
    return config.Space.model_validate(space_dict)
  except ValidationError as e:
    rprint("[bold red]\nInvalid space\n[/bold red]")
    rprint(f"Errors: {e.error_count()}")
    for error in e.errors():
      rprint(f"{error['loc']}: {error['msg']}")
    raise typer.Abort()


@app.command(name="add")
def add_space(
  name: str = typer.Argument(
    ...,
    help="Name of the new pomodoro space",
  ),
  focus: Optional[int] = typer.Option(
    None,
    "--focus",
    help="Focus duration",
  ),
  short_break: Optional[int] = typer.Option(
    None,
    "--short-break",
    help="Short break duration",
  ),
  long_break: Optional[int] = typer.Option(
    None,
    "--long-break",
    help="Long break duration",
  ),
  sessions: Optional[int] = typer.Option(
    None,
    "--sessions",
    help="Sessions before long break",
  ),
  color: Optional[str] = typer.Option(
    None,
    "--color",
    help="Base color",
  ),
):
  """
  Add a new space.

  If options are provided, creates space non-interactively.
  Otherwise, prompts for each value.
  """
  if name in config.get_space_names():
    rprint(f'Space [bold red]"{name}"[/bold red] already exists')
    return

  if any(v is not None for v in [focus, short_break, long_break, sessions, color]):
    space_dict = _add_space_non_interactive(focus, short_break, long_break, sessions, color)
  else:
    space_dict = _add_space_interactive()

  space = _validate_space(space_dict)
  space = config.add_space(name, space)

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] already exists')
  else:
    rprint(f'Space [bold green]"{name}"[/bold green] added')


def _add_space_non_interactive(
  focus: Optional[int],
  short_break: Optional[int],
  long_break: Optional[int],
  sessions: Optional[int],
  color: Optional[str],
) -> dict:
  """Non-interactive space creation with defaults."""

  spaces = config.get_spaces()
  defaults = spaces.get("work", Space())

  return {
    "focus_duration": (focus if focus is not None else defaults.focus_duration),
    "short_break_duration": (
      short_break if short_break is not None else defaults.short_break_duration
    ),
    "long_break_duration": (long_break if long_break is not None else defaults.long_break_duration),
    "sessions_before_long_break": (
      sessions if sessions is not None else defaults.sessions_before_long_break
    ),
    "color": (color if color is not None else defaults.color),
  }


def _add_space_interactive() -> dict:
  """Interactive space creation."""

  rprint("Enter the durations in minutes.")
  focus = typer.prompt("Focus duration", type=int)
  short_break = typer.prompt("Short break duration", type=int)
  long_break = typer.prompt("Long break duration", type=int)
  sessions = typer.prompt("Sessions", type=int)
  color = typer.prompt("Color", type=str)

  return {
    "focus_duration": focus,
    "short_break_duration": short_break,
    "long_break_duration": long_break,
    "sessions_before_long_break": sessions,
    "color": color,
  }


@app.command(name="edit")
def edit_space(
  name: str = typer.Argument(
    ...,
    help="Name of the pomodoro space",
    autocompletion=complete_spaces,
  ),
  focus: Optional[int] = typer.Option(
    None,
    "--focus",
    help="Focus duration",
  ),
  short_break: Optional[int] = typer.Option(
    None,
    "--short-break",
    help="Short break duration",
  ),
  long_break: Optional[int] = typer.Option(
    None,
    "--long-break",
    help="Long break duration",
  ),
  sessions: Optional[int] = typer.Option(
    None,
    "--sessions",
    help="Sessions before long break",
  ),
  color: Optional[str] = typer.Option(
    None,
    "--color",
    help="Base color",
  ),
):
  """
  Edit an existing profile.

  If options are provided, updates only those values.
  Otherwise, shows current values and prompts for new ones.
  """
  space = config.get_spaces().get(name)

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
    return

  if any(v is not None for v in [focus, short_break, long_break, sessions, color]):
    space_dict = _edit_space_non_interactive(space, focus, short_break, long_break, sessions, color)
  else:
    space_dict = _edit_space_interactive(name, space)

  space = _validate_space(space_dict)
  space = config.edit_space(name, space.model_dump())

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] already exists')
  else:
    rprint(f'Space [bold green]"{name}"[/bold green] edited')


def _edit_space_non_interactive(
  space: Space,
  focus: Optional[int],
  short_break: Optional[int],
  long_break: Optional[int],
  sessions: Optional[int],
  color: Optional[str],
) -> dict:
  """Non-interactive space creation with defaults."""

  return {
    "focus_duration": (focus if focus is not None else space.focus_duration),
    "short_break_duration": (
      short_break if short_break is not None else space.short_break_duration
    ),
    "long_break_duration": (long_break if long_break is not None else space.long_break_duration),
    "sessions_before_long_break": (
      sessions if sessions is not None else space.sessions_before_long_break
    ),
    "color": (color if color is not None else space.color),
  }


def _edit_space_interactive(name: str, space: Space) -> dict:
  """Interactive space editing."""

  show_space(name)

  rprint("\nEnter the durations in minutes.")
  focus = typer.prompt("Focus duration", default=space.focus_duration, type=int)
  short_break = typer.prompt("Short break duration", default=space.short_break_duration, type=int)
  long_break = typer.prompt("Long break duration", default=space.long_break_duration, type=int)
  sessions = typer.prompt("Sessions", default=space.sessions_before_long_break, type=int)
  color = typer.prompt("Color", default=space.color, type=str)

  return {
    "focus_duration": focus,
    "short_break_duration": short_break,
    "long_break_duration": long_break,
    "sessions_before_long_break": sessions,
    "color": color,
  }


@app.command(name="rm")
def remove_space(
  name: str = typer.Argument(
    ...,
    help="Name of the space to remove",
    autocompletion=complete_spaces,
  ),
  force: bool = typer.Option(
    False,
    "--force",
    "-f",
    help="Delete without confirmation",
  ),
):
  """Remove a pomodoro space."""
  if name not in config.get_space_names():
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
    return

  if name == state.get_active_space_name():
    rprint(f'Cannot delete active space [bold red]"{name}"[/bold red]')
    return

  if not force:
    typer.confirm(f'Delete the "{name}" space?', abort=True)

  space = config.remove_space(name)

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
  else:
    rprint(f'Space [bold green]"{name}"[/bold green] removed permanantly')


@app.command(name="rename")
def rename_space(
  name: str = typer.Argument(
    ...,
    help="Name of the space to rename",
    autocompletion=complete_spaces,
  ),
  new_name: Optional[str] = typer.Option(
    None,
    "--new-name",
    "-to",
    help="New name of the space",
  ),
):
  """Rename a pomodoro space."""
  if name not in config.get_space_names():
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
    return

  if not new_name:
    new_name_input = typer.prompt(f'New name for "{name}" space')
    new_name = str(new_name_input)

  if new_name in config.get_space_names():
    rprint(f'Space [bold red]"{name}"[/bold red] already exists')
    return

  rename_active_space = name == state.get_active_space_name()

  space = config.remove_space(name)

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] does not exist')
    return

  space = config.add_space(new_name, space)

  if not space:
    rprint(f'Space [bold red]"{name}"[/bold red] already exists')
  else:
    rprint(
      f'Space [bold green]"{name}"[/bold green] renamed to [bold green]"{new_name}"[/bold green]'
    )

  if rename_active_space:
    set_space(new_name)

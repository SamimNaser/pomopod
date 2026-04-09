from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pomopod.core import config, state

daemon = typer.Typer()
notification = typer.Typer()
app = typer.Typer()
console = Console()


def complete_spaces(incomplete: str) -> list[str]:
  return [p for p in config.get_space_names() if p.startswith(incomplete)]


@app.command(name="show")
def show_configuration():
  """Show all pomopod configuration."""
  daemon_settings = config.get_daemon_settings()
  notification_settings = config.get_notification_settings()

  table = Table(title="PomoPod Configuration")
  table.add_column("Setting", style="cyan")
  table.add_column("Value", style="green")

  table.add_row("Active Space", state.get_active_space_name())
  table.add_row("Daemon Host", daemon_settings.host)
  table.add_row("Daemon Port", str(daemon_settings.port))
  table.add_row("Notifications", "Enabled" if notification_settings.enabled else "Disabled")

  console.print(table)


@app.command(name="daemon")
def set_daemon_settings(
  host: Optional[str] = typer.Option(
    None,
    "--host",
    "-h",
    help="Daemon host",
  ),
  port: Optional[int] = typer.Option(
    None,
    "--port",
    "-p",
    help="Daemon port",
  ),
):
  """Set daemon settings."""
  config.update_daemon_settings(host, port)


@app.command(name="notif")
def set_notification_settings(
  enable: Optional[bool] = typer.Option(
    None,
    "--enable/--disable",
    help="Enable or disable notifications",
  ),
):
  """Toggle notification settings."""
  if enable is None:
    setting = config.get_notification_settings()
    status = "[green]enabled[/green]" if setting.enabled else "[red]disabled[/red]"
    rprint(f"Notifications are {status}")
    return

  if enable:
    rprint("Notifications are [green]enabled[/green]")
  else:
    rprint("Notifications are [red]disabled[/red]")
  config.update_notification_settings(enable)

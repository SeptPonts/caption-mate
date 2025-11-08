from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ...core.config import Config

console = Console()


@click.group()
def config():
    """Configuration management commands"""
    pass


@config.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing config file")
@click.pass_context
def init(ctx, overwrite):
    """Initialize configuration file with interactive setup"""
    config_path = ctx.obj.get("config_file")
    if config_path:
        config_path = Path(config_path)
    else:
        config_path = Config.get_default_config_path()

    if config_path.exists() and not overwrite:
        console.print(f"[yellow]Config file already exists at {config_path}[/yellow]")
        console.print(
            "Use --overwrite to replace it or use 'config set' to modify values"
        )
        return

    console.print("[bold blue]Caption-Mate Configuration Setup[/bold blue]")
    console.print("Let's configure your Caption-Mate settings.\n")

    # Initialize config
    cfg = Config()

    # NAS configuration
    console.print("\n[bold]NAS Configuration[/bold]")
    protocol = Prompt.ask("NAS Protocol", choices=["smb", "nfs", "sftp"], default="smb")
    cfg.nas.protocol = protocol

    host = Prompt.ask("NAS Host/IP Address")
    cfg.nas.host = host

    if protocol == "smb":
        port = Prompt.ask("Port", default="445")
        cfg.nas.port = int(port)
        domain = Prompt.ask("Domain", default="WORKGROUP")
        cfg.nas.domain = domain
    elif protocol == "nfs":
        port = Prompt.ask("Port", default="2049")
        cfg.nas.port = int(port)
    elif protocol == "sftp":
        port = Prompt.ask("Port", default="22")
        cfg.nas.port = int(port)

    username = Prompt.ask("NAS Username")
    cfg.nas.username = username

    password = Prompt.ask("NAS Password", password=True)
    cfg.nas.password = password

    # Subtitles configuration
    console.print("\n[bold]Subtitles Configuration[/bold]")
    languages = Prompt.ask("Preferred Languages (comma-separated)", default="zh-cn,en")
    cfg.subtitles.languages = [lang.strip() for lang in languages.split(",")]

    # Save configuration
    cfg.save(config_path)
    console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")

    # Validate configuration
    errors = cfg.validate()
    if errors:
        console.print("\n[yellow]Configuration warnings:[/yellow]")
        for error in errors:
            console.print(f"  • {error}")


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Set a configuration value (e.g., 'nas.host 192.168.1.100')"""
    config_path = ctx.obj.get("config_file")

    try:
        cfg = Config.load(config_path)
        cfg.set_value(key, value)
        cfg.save(config_path)
        console.print(f"[green]✓[/green] Set {key} = {value}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@config.command()
@click.argument("key", required=False)
@click.pass_context
def show(ctx, key):
    """Show configuration values"""
    config_path = ctx.obj.get("config_file")

    try:
        cfg = Config.load(config_path)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise click.Abort()

    if key:
        # Show specific key
        try:
            value = cfg.get_value(key)
            console.print(f"{key} = {value}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()
    else:
        # Show all configuration
        table = Table(title="Caption-Mate Configuration")
        table.add_column("Section", style="cyan")
        table.add_column("Key", style="magenta")
        table.add_column("Value", style="white")

        # NAS
        table.add_row("nas", "protocol", cfg.nas.protocol)
        table.add_row("", "host", cfg.nas.host or "[dim]not set[/dim]")
        table.add_row("", "port", str(cfg.nas.port))
        table.add_row("", "username", cfg.nas.username or "[dim]not set[/dim]")
        table.add_row(
            "", "password", "***" if cfg.nas.password else "[dim]not set[/dim]"
        )
        table.add_row("", "domain", cfg.nas.domain)

        # Subtitles
        table.add_row("subtitles", "languages", ", ".join(cfg.subtitles.languages))
        table.add_row("", "formats", ", ".join(cfg.subtitles.formats))
        table.add_row(
            "", "output_dir", cfg.subtitles.output_dir or "[dim]same as video[/dim]"
        )
        table.add_row("", "naming_pattern", cfg.subtitles.naming_pattern)

        # Scanning
        table.add_row(
            "scanning", "video_extensions", ", ".join(cfg.scanning.video_extensions)
        )
        table.add_row("", "recursive", str(cfg.scanning.recursive))
        table.add_row("", "skip_existing", str(cfg.scanning.skip_existing))
        table.add_row("", "cache_duration", f"{cfg.scanning.cache_duration}s")

        console.print(table)

        # Show config file path
        actual_path = config_path if config_path else Config.get_default_config_path()
        console.print(f"\nConfig file: {actual_path}")

        # Show validation errors
        errors = cfg.validate()
        if errors:
            console.print("\n[yellow]Configuration issues:[/yellow]")
            for error in errors:
                console.print(f"  • {error}")


@config.command()
@click.pass_context
def path(ctx):
    """Show configuration file path"""
    config_path = ctx.obj.get("config_file")
    if config_path:
        console.print(f"Using config file: {config_path}")
    else:
        default_path = Config.get_default_config_path()
        console.print(f"Default config file: {default_path}")
        if default_path.exists():
            console.print("[green]✓[/green] Config file exists")
        else:
            console.print(
                "[yellow]![/yellow] Config file does not exist (run 'config init')"
            )

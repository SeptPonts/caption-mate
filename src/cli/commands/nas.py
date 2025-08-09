from typing import Any, Dict

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ...core.config import Config
from ...core.nas_client import NASClient

console = Console()


@click.group()
def nas():
    """NAS connection and file operations"""
    pass


@nas.command()
@click.pass_context
def test(ctx):
    """Test NAS connection"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print("[red]Configuration errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            console.print("\nRun 'caption-mate config init' to set up configuration")
            raise click.Abort()

        with console.status("[bold green]Testing NAS connection..."):
            with NASClient(config) as client:
                success = client.test_connection()

        if success:
            console.print("[green]✓[/green] NAS connection successful")

            # Try to list shares
            try:
                with NASClient(config) as client:
                    shares = client.list_shares()
                if shares:
                    console.print(f"Found {len(shares)} shares: {', '.join(shares)}")
                else:
                    console.print("No shares found (this might be normal)")
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not list shares: {e}")
        else:
            console.print("[red]✗[/red] NAS connection failed")
            console.print("Check your configuration with 'caption-mate config show'")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@nas.command()
@click.argument("path", default="/")
@click.option("--long", "-l", is_flag=True, help="Show detailed information")
@click.option("--recursive", "-r", is_flag=True, help="List directories recursively")
@click.option("--only-dirs", is_flag=True, help="Show only directories")
@click.option("--only-files", is_flag=True, help="Show only files")
@click.option("--filter", "pattern", help='Filter files by pattern (e.g., "*.mp4")')
@click.pass_context
def ls(ctx, path, long, recursive, only_dirs, only_files, pattern):
    """List files and directories in NAS path"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        with NASClient(config) as client:
            if not client.path_exists(path):
                console.print(f"[red]Error:[/red] Path '{path}' does not exist")
                raise click.Abort()

            if recursive:
                _list_recursive(client, path, long, only_dirs, only_files, pattern)
            else:
                _list_directory(client, path, long, only_dirs, only_files, pattern)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _list_directory(
    client: NASClient,
    path: str,
    long: bool,
    only_dirs: bool,
    only_files: bool,
    pattern: str,
):
    """List a single directory"""
    try:
        entries = client.list_directory(path, pattern)

        # Filter by type
        if only_dirs:
            entries = [e for e in entries if e.is_dir]
        elif only_files:
            entries = [e for e in entries if not e.is_dir]

        if not entries:
            console.print("[dim]No files found[/dim]")
            return

        if long:
            table = Table()
            table.add_column("Type", width=4)
            table.add_column("Name")
            table.add_column("Size", justify="right")
            table.add_column("Modified")

            for entry in entries:
                icon = "📁" if entry.is_dir else "📄"
                size_str = "-" if entry.is_dir else entry.size_human
                modified_str = (
                    entry.modified_time.strftime("%Y-%m-%d %H:%M")
                    if entry.modified_time
                    else "-"
                )

                table.add_row(icon, entry.name, size_str, modified_str)

            console.print(table)
        else:
            # Simple listing
            for entry in entries:
                if entry.is_dir:
                    console.print(f"📁 {entry.name}/")
                else:
                    console.print(f"📄 {entry.name}")

    except Exception as e:
        console.print(f"[red]Error listing {path}:[/red] {e}")


def _list_recursive(
    client: NASClient,
    path: str,
    long: bool,
    only_dirs: bool,
    only_files: bool,
    pattern: str,
):
    """List directories recursively"""

    def list_recursive_inner(current_path: str, prefix: str = ""):
        try:
            entries = client.list_directory(current_path, pattern)

            # Filter by type
            if only_dirs:
                entries = [e for e in entries if e.is_dir]
            elif only_files:
                entries = [e for e in entries if not e.is_dir]

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                current_prefix = "└── " if is_last else "├── "

                icon = "📁" if entry.is_dir else "📄"
                if long and not entry.is_dir:
                    console.print(
                        f"{prefix}{current_prefix}{icon} {entry.name} "
                        f"({entry.size_human})"
                    )
                else:
                    console.print(f"{prefix}{current_prefix}{icon} {entry.name}")

                if entry.is_dir:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    list_recursive_inner(entry.path, next_prefix)

        except Exception as e:
            console.print(f"{prefix}[red]Error accessing {current_path}: {e}[/red]")

    console.print(f"📁 {path}")
    list_recursive_inner(path)


@nas.command()
@click.argument("path", default="/")
@click.option("--depth", default=2, help="Maximum depth to traverse")
@click.pass_context
def tree(ctx, path, depth):
    """Show directory tree structure"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        with console.status(f"[bold green]Building directory tree for {path}..."):
            with NASClient(config) as client:
                if not client.path_exists(path):
                    console.print(f"[red]Error:[/red] Path '{path}' does not exist")
                    raise click.Abort()

                tree_data = client.get_directory_tree(path, max_depth=depth)

        # Build rich tree display
        tree = Tree(f"📁 {path}")
        _build_tree_display(tree, tree_data)
        console.print(tree)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _build_tree_display(parent_tree: Tree, tree_data: Dict[str, Any]):
    """Recursively build tree display"""
    for name, info in tree_data.items():
        if info["type"] == "directory":
            dir_node = parent_tree.add(f"📁 {name}")
            if info["children"]:
                _build_tree_display(dir_node, info["children"])
        else:
            # File
            size_str = ""
            if "size" in info and info["size"] > 0:
                size = info["size"]
                for unit in ["B", "KB", "MB", "GB"]:
                    if size < 1024.0:
                        size_str = f" ({size:.1f}{unit})"
                        break
                    size /= 1024.0
            parent_tree.add(f"📄 {name}{size_str}")


@nas.command()
@click.argument("path")
@click.option("--recursive/--no-recursive", default=True, help="Scan subdirectories")
@click.option("--extensions", help="Comma-separated list of video extensions")
@click.pass_context
def scan(ctx, path, recursive, extensions):
    """Scan for video files in the specified path"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        # Override extensions if provided
        if extensions:
            config.scanning.video_extensions = [
                ext.strip() for ext in extensions.split(",")
            ]

        with console.status(f"[bold green]Scanning for video files in {path}..."):
            with NASClient(config) as client:
                if not client.path_exists(path):
                    console.print(f"[red]Error:[/red] Path '{path}' does not exist")
                    raise click.Abort()

                video_files = client.scan_video_files(path, recursive)

        if not video_files:
            console.print("[yellow]No video files found[/yellow]")
            return

        console.print(f"\n[green]Found {len(video_files)} video files:[/green]")

        table = Table()
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Path", style="dim")

        for file_entry in video_files:
            table.add_row(file_entry.name, file_entry.size_human, file_entry.path)

        console.print(table)

        # Show summary by extension
        ext_counts = {}
        for file_entry in video_files:
            ext = file_entry.name.split(".")[-1].lower()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if len(ext_counts) > 1:
            file_types = ", ".join(
                f"{ext}({count})" for ext, count in ext_counts.items()
            )
            console.print(f"\n[dim]File types: {file_types}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@nas.command()
@click.pass_context
def list(ctx):
    """List previously scanned video files (placeholder for future caching)"""
    console.print("[yellow]Feature not yet implemented[/yellow]")
    console.print("This will show cached scan results in a future version")

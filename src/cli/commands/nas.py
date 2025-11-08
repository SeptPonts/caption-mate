from pathlib import Path
from typing import Any, Dict

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ...core.config import Config
from ...core.nas_client import NASClient
from ...core.subtitle_matcher import SubtitleMatcher
from ...models.subtitle import SubtitleFile
from ...models.video import VideoFile

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


def _load_and_validate_config(ctx):
    """Load and validate configuration"""
    config = Config.load(ctx.obj.get("config_file"))
    errors = config.validate()
    if errors:
        console.print("[red]Configuration errors found. Run 'config init' first.[/red]")
        raise click.Abort()
    return config


def _detect_language_from_filename(filename: str, config) -> str:
    """Detect language from subtitle filename"""
    name = filename.lower()

    # Common language patterns
    language_patterns = {
        "zh-cn": [".zh.", ".chi.", ".chs.", ".chinese.", "chinese", ".中文.", ".简体."],
        "zh-tw": [".cht.", ".繁体.", ".traditional."],
        "en": [".en.", ".eng.", ".english.", "english"],
        "ja": [".jp.", ".jpn.", ".japanese.", "japanese"],
        "ko": [".ko.", ".kor.", ".korean.", "korean"],
        "fr": [".fr.", ".fre.", ".french.", "french"],
        "de": [".de.", ".ger.", ".german.", "german"],
        "es": [".es.", ".spa.", ".spanish.", "spanish"],
        "pt": [".pt.", ".por.", ".portuguese.", "portuguese"],
        "ru": [".ru.", ".rus.", ".russian.", "russian"],
    }

    # Check for language patterns in filename
    for lang_code, patterns in language_patterns.items():
        if any(pattern in name for pattern in patterns):
            return lang_code

    # If no pattern found, use first preferred language from config
    if config.subtitles.languages:
        return config.subtitles.languages[0]

    # Final fallback
    return "zh-cn"


def _scan_directory_for_files(nas_client, path, config):
    """Scan directory and separate video and subtitle files"""
    if not nas_client.path_exists(path):
        console.print(f"[red]Error:[/red] Path '{path}' does not exist")
        raise click.Abort()

    all_entries = nas_client.list_directory(path)
    video_extensions = set(config.scanning.video_extensions)
    subtitle_extensions = {".srt", ".ass", ".ssa", ".vtt", ".sub"}

    video_files = []
    subtitle_files = []

    for entry in all_entries:
        if entry.is_dir:
            continue

        file_ext = Path(entry.name).suffix.lower()
        if file_ext in video_extensions:
            video_file = VideoFile(
                filename=entry.name,
                file_path=entry.path,
                file_size=entry.size,
                nas_path=entry.path,
                modified_time=entry.modified_time,
            )
            video_files.append(video_file)
        elif file_ext in subtitle_extensions:
            detected_language = _detect_language_from_filename(entry.name, config)
            subtitle_file = SubtitleFile(
                filename=entry.name,
                file_path=entry.path,
                language=detected_language,
                format=file_ext.lstrip("."),
                video_filename="",
                file_size=entry.size,
            )
            subtitle_files.append(subtitle_file)

    return video_files, subtitle_files


def _perform_matching(video_files, subtitle_files, threshold, mode="regex"):
    """Perform matching and return rename operations"""
    matcher = SubtitleMatcher(similarity_threshold=threshold, mode=mode)
    match_results = matcher.match_directory(video_files, subtitle_files)
    successful_matches = [result for result in match_results if result.has_match]

    if not successful_matches:
        return []

    return matcher.plan_rename_operations(successful_matches, "")


async def _perform_matching_async(video_files, subtitle_files, threshold, mode="ai"):
    """Async version supporting AI matching"""
    matcher = SubtitleMatcher(similarity_threshold=threshold, mode=mode)
    match_results = await matcher.match_directory_async(video_files, subtitle_files)
    successful_matches = [result for result in match_results if result.has_match]

    if not successful_matches:
        return []

    return matcher.plan_rename_operations(successful_matches, "")


def _display_match_results(rename_operations, config, path, force):
    """Display match results in a table"""
    console.print(f"\n[green]Found {len(rename_operations)} matches:[/green]")

    table = Table()
    table.add_column("Video File", style="cyan")
    table.add_column("Subtitle File", style="magenta")
    table.add_column("Confidence", justify="center")
    table.add_column("New Name", style="yellow")
    table.add_column("Action", justify="center")

    for operation in rename_operations:
        confidence_color = (
            "green"
            if operation.confidence >= 0.95
            else "yellow"
            if operation.confidence >= 0.8
            else "red"
        )

        action = "✓ Rename" if operation.needs_rename else "- Skip"
        if not force and operation.needs_rename:
            target_path = str(Path(path) / operation.new_name)
            with NASClient(config) as nas_client:
                if nas_client.path_exists(target_path):
                    action = "! Exists"

        table.add_row(
            operation.target_video.filename,
            operation.old_name,
            f"[{confidence_color}]{operation.confidence:.2f}[/{confidence_color}]",
            operation.new_name,
            action,
        )

    console.print(table)


def _execute_rename_operations(rename_operations, config, path, force):
    """Execute rename operations and return results"""
    results = {"renamed": 0, "skipped": 0, "errors": 0}

    with NASClient(config) as nas_client:
        for operation in rename_operations:
            if not operation.needs_rename:
                results["skipped"] += 1
                continue

            old_path = operation.subtitle_file.file_path
            new_path = str(Path(path) / operation.new_name)

            if nas_client.path_exists(new_path) and not force:
                console.print(
                    f"[yellow]Skipping {operation.new_name}: file exists[/yellow]"
                )
                results["skipped"] += 1
                continue

            try:
                success = nas_client.rename_file(old_path, new_path)
                if success:
                    results["renamed"] += 1
                    console.print(
                        f"[green]✓[/green] Renamed: {operation.old_name} → "
                        f"{operation.new_name}"
                    )
                else:
                    results["errors"] += 1
                    console.print(
                        f"[red]✗[/red] Failed to rename: {operation.old_name}"
                    )
            except Exception as e:
                results["errors"] += 1
                console.print(f"[red]✗[/red] Error renaming {operation.old_name}: {e}")

    return results


def _display_summary(results):
    """Display execution summary"""
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"[green]✓ Renamed: {results['renamed']}[/green]")
    console.print(f"[yellow]- Skipped: {results['skipped']}[/yellow]")
    console.print(f"[red]✗ Errors: {results['errors']}[/red]")


@nas.command()
@click.argument("path")
@click.option("--dry-run", is_flag=True, help="Preview matches without renaming")
@click.option("--force", is_flag=True, help="Overwrite existing subtitles")
@click.option("--threshold", default=0.8, help="Similarity threshold (0.0-1.0)")
@click.option(
    "--mode", default="ai", type=click.Choice(["regex", "ai"]), help="Matching mode"
)
@click.pass_context
def match(ctx, path, dry_run, force, threshold, mode):
    """Match and rename subtitle files to video files in NAS directory"""
    try:
        # Load and validate configuration
        config = _load_and_validate_config(ctx)

        console.print(f"[bold blue]Matching subtitles in: {path}[/bold blue]")
        console.print(f"Similarity threshold: {threshold}")
        console.print(f"Matching mode: {mode}")
        console.print(f"Mode: {'Preview' if dry_run else 'Execute'}")

        # Scan directory for files
        with console.status("[bold green]Scanning directory..."):
            with NASClient(config) as nas_client:
                video_files, subtitle_files = _scan_directory_for_files(
                    nas_client, path, config
                )

        # Check if we have files to work with
        if not video_files:
            console.print(f"[yellow]No video files found in {path}[/yellow]")
            return

        if not subtitle_files:
            console.print(f"[yellow]No subtitle files found in {path}[/yellow]")
            return

        console.print(
            f"Found {len(video_files)} video files and "
            f"{len(subtitle_files)} subtitle files"
        )

        # Perform matching with mode-specific status
        if mode == "ai":
            status_msg = "[bold blue]Calling AI model (this may take a while)..."
            with console.status(status_msg):
                import asyncio

                rename_operations = asyncio.run(
                    _perform_matching_async(
                        video_files, subtitle_files, threshold, mode
                    )
                )
        else:
            with console.status("[bold green]Matching files..."):
                rename_operations = _perform_matching(
                    video_files, subtitle_files, threshold, mode
                )

        if not rename_operations:
            console.print("[yellow]No matches found above threshold[/yellow]")
            return

        # Display results
        _display_match_results(rename_operations, config, path, force)

        if dry_run:
            console.print("\n[bold]Dry run mode - no files were renamed[/bold]")
            return

        # Get user confirmation before proceeding
        operations_count = len([op for op in rename_operations if op.needs_rename])
        if operations_count > 0:
            console.print(
                f"\n[yellow]About to rename {operations_count} file(s).[/yellow]"
            )
            if not click.confirm("Do you want to proceed with the rename operations?"):
                console.print("[blue]Operation cancelled by user.[/blue]")
                return

        # Execute rename operations
        with console.status("[bold green]Renaming files..."):
            results = _execute_rename_operations(rename_operations, config, path, force)

        # Show summary
        _display_summary(results)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@nas.command()
@click.argument("local_paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("nas_path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files on NAS")
@click.option(
    "--dry-run", is_flag=True, help="Preview upload without transferring files"
)
@click.pass_context
def upload(ctx, local_paths, nas_path, overwrite, dry_run):
    """Upload local files or directories to NAS

    Examples:
        # Upload single file
        caption-mate nas upload /local/subtitle.srt /Movies/

        # Upload multiple files
        caption-mate nas upload /local/sub1.srt /local/sub2.ass /Movies/

        # Upload directory
        caption-mate nas upload /local/subtitles/ /Movies/subtitles/

    Common workflow:
        1. Upload subtitles to NAS: nas upload /local/subs/ /Movies/
        2. Match to videos: nas match /Movies/ --mode ai
    """
    try:
        config = _load_and_validate_config(ctx)

        console.print(f"[bold blue]Upload to NAS: {nas_path}[/bold blue]")
        console.print(f"Mode: {'Preview' if dry_run else 'Execute'}")

        # Check NAS path exists
        with NASClient(config) as nas_client:
            if not nas_client.path_exists(nas_path):
                console.print(f"[yellow]NAS path does not exist: {nas_path}[/yellow]")
                if click.confirm("Create directory?"):
                    nas_client.create_directory(nas_path)
                    console.print(f"[green]✓[/green] Created directory: {nas_path}")
                else:
                    raise click.Abort()

        # Collect files to upload
        from pathlib import Path as LocalPath

        upload_items = []
        for local_path in local_paths:
            local = LocalPath(local_path)
            if local.is_file():
                upload_items.append(("file", str(local)))
            elif local.is_dir():
                upload_items.append(("dir", str(local)))

        if not upload_items:
            console.print("[yellow]No valid files or directories to upload[/yellow]")
            return

        # Preview
        console.print("\n[bold]Items to upload:[/bold]")
        table = Table()
        table.add_column("Type", width=10)
        table.add_column("Local Path", style="cyan")
        table.add_column("Size", justify="right")

        total_size = 0
        for item_type, item_path in upload_items:
            local = LocalPath(item_path)
            if item_type == "file":
                size = local.stat().st_size
                total_size += size
                size_human = _format_size(size)
                table.add_row("File", str(local), size_human)
            else:
                # Count directory contents
                file_count = sum(1 for _ in local.rglob("*") if _.is_file())
                table.add_row("Directory", str(local), f"{file_count} files")

        console.print(table)

        if dry_run:
            console.print("\n[bold]Dry run mode - no files uploaded[/bold]")
            return

        # Confirm upload
        if not click.confirm(f"\nUpload {len(upload_items)} item(s) to {nas_path}?"):
            console.print("[blue]Upload cancelled[/blue]")
            return

        # Execute upload
        stats = {"uploaded": 0, "failed": 0, "skipped": 0}

        with NASClient(config) as nas_client:
            for item_type, item_path in upload_items:
                try:
                    if item_type == "file":
                        target = f"{nas_path.rstrip('/')}/{LocalPath(item_path).name}"

                        # Check if file exists
                        if nas_client.path_exists(target) and not overwrite:
                            console.print(
                                f"[yellow]Skipping {LocalPath(item_path).name}: "
                                "file exists[/yellow]"
                            )
                            stats["skipped"] += 1
                            continue

                        nas_client.upload_file(item_path, nas_path)
                        stats["uploaded"] += 1
                        console.print(
                            f"[green]✓[/green] Uploaded: {LocalPath(item_path).name}"
                        )
                    else:
                        dir_stats = nas_client.upload_directory(
                            item_path, nas_path, True
                        )
                        stats["uploaded"] += dir_stats["uploaded"]
                        stats["failed"] += dir_stats["failed"]
                        console.print(
                            f"[green]✓[/green] Uploaded directory: "
                            f"{LocalPath(item_path).name} "
                            f"({dir_stats['uploaded']} files)"
                        )

                except Exception as e:
                    stats["failed"] += 1
                    console.print(f"[red]✗[/red] Failed to upload {item_path}: {e}")

        # Summary
        console.print("\n[bold]Upload Summary:[/bold]")
        console.print(f"[green]✓ Uploaded: {stats['uploaded']}[/green]")
        console.print(f"[yellow]- Skipped: {stats['skipped']}[/yellow]")
        console.print(f"[red]✗ Failed: {stats['failed']}[/red]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _format_size(size: int) -> str:
    """Format file size in human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"

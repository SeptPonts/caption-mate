import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ...core.config import Config
from ...core.nas_client import NASClient
from ...core.subtitle_service import SubtitleService
from ...core.video_analyzer import VideoAnalyzer

console = Console()


@click.group()
def subtitles():
    """Subtitle search and download commands"""
    pass


@subtitles.command()
@click.argument("query")
@click.option(
    "--language", "-l", multiple=True, help="Language codes (e.g., zh-cn, en)"
)
@click.option("--limit", default=10, help="Maximum number of results")
@click.pass_context
def search(ctx, query, language, limit):
    """Search for subtitles by movie/show name"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        # Override languages if provided
        search_languages = list(language) if language else config.subtitles.languages

        async def search_subtitles():
            service = SubtitleService(config)
            async with service.api:
                results = await service.api.search_subtitles(
                    query=query, languages=search_languages
                )
                return results[:limit]

        with console.status(f"[bold green]Searching for '{query}'..."):
            results = asyncio.run(search_subtitles())

        if not results:
            console.print(f"[yellow]No subtitles found for '{query}'[/yellow]")
            return

        console.print(f"\n[green]Found {len(results)} subtitles for '{query}':[/green]")

        table = Table()
        table.add_column("Language", style="cyan")
        table.add_column("Filename", style="magenta")
        table.add_column("Downloads", justify="right")
        table.add_column("Rating", justify="right")
        table.add_column("Size", justify="right")
        table.add_column("Release", style="dim")

        for subtitle in results:
            table.add_row(
                subtitle.language,
                subtitle.filename,
                str(subtitle.download_count),
                f"{subtitle.rating:.1f}",
                subtitle.size_human,
                subtitle.release_name[:30] + "..."
                if len(subtitle.release_name) > 30
                else subtitle.release_name,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@subtitles.command()
@click.argument("video_path")
@click.option("--language", "-l", multiple=True, help="Language codes")
@click.option("--output-dir", "-o", help="Output directory for subtitle files")
@click.option("--dry-run", is_flag=True, help="Preview what would be downloaded")
@click.pass_context
def download(ctx, video_path, language, output_dir, dry_run):
    """Download subtitles for a specific video file"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        # Determine if it's a NAS path or local path
        is_nas_path = video_path.startswith("/")

        if is_nas_path:
            # NAS path - need to connect to NAS to get file info
            with NASClient(config) as nas_client:
                if not nas_client.path_exists(video_path):
                    console.print(
                        f"[red]Error:[/red] Video file not found: {video_path}"
                    )
                    raise click.Abort()

                # Get file info from NAS
                entries = nas_client.list_directory(
                    Path(video_path).parent.as_posix(), pattern=Path(video_path).name
                )
                if not entries:
                    console.print(
                        f"[red]Error:[/red] Could not get file info: {video_path}"
                    )
                    raise click.Abort()

                file_entry = entries[0]
                video_size = file_entry.size
        else:
            # Local path
            local_path = Path(video_path)
            if not local_path.exists():
                console.print(f"[red]Error:[/red] Video file not found: {video_path}")
                raise click.Abort()

            video_size = local_path.stat().st_size

        # Override languages if provided
        search_languages = list(language) if language else config.subtitles.languages

        async def download_subtitle():
            service = SubtitleService(config)

            # Search for subtitles
            console.print("[bold blue]Searching for subtitles...[/bold blue]")
            subtitles = await service.search_for_video(video_path, video_size)

            if not subtitles:
                console.print("[yellow]No subtitles found[/yellow]")
                return None

            # Filter by requested languages
            filtered_subtitles = [
                s for s in subtitles if s.language in search_languages
            ]

            if not filtered_subtitles:
                languages = ", ".join(search_languages)
                console.print(
                    f"[yellow]No subtitles found for languages: {languages}[/yellow]"
                )
                return None

            if dry_run:
                console.print("\n[bold]Would download:[/bold]")
                table = Table()
                table.add_column("Language")
                table.add_column("Filename")
                table.add_column("Downloads", justify="right")
                table.add_column("Size", justify="right")

                for subtitle in filtered_subtitles[: len(search_languages)]:
                    table.add_row(
                        subtitle.language,
                        subtitle.filename,
                        str(subtitle.download_count),
                        subtitle.size_human,
                    )

                console.print(table)
                return None

            # Download best subtitle for each requested language
            downloaded = []

            for lang in search_languages:
                lang_subtitles = [s for s in filtered_subtitles if s.language == lang]
                if not lang_subtitles:
                    continue

                best_subtitle = lang_subtitles[0]  # Already sorted by quality

                console.print(
                    f"[bold green]Downloading {lang} subtitle...[/bold green]"
                )

                # Determine output path
                if output_dir:
                    output_path = Path(output_dir)
                else:
                    output_path = Path(video_path).parent

                # Generate filename
                video_filename = Path(video_path).name
                subtitle_ext = Path(best_subtitle.filename).suffix.lstrip(".")
                subtitle_filename = service.generate_subtitle_filename(
                    video_filename, lang, subtitle_ext
                )

                full_output_path = output_path / subtitle_filename

                # Download
                success = await service.api.download_subtitle(
                    best_subtitle, full_output_path
                )

                if success:
                    downloaded.append((lang, full_output_path))
                    console.print(
                        f"[green]✓[/green] Downloaded {lang}: {full_output_path}"
                    )
                else:
                    console.print(f"[red]✗[/red] Failed to download {lang} subtitle")

            return downloaded

        with console.status("[bold green]Processing..."):
            result = asyncio.run(download_subtitle())

        if result:
            console.print(
                f"\n[green]Successfully downloaded {len(result)} subtitle(s)[/green]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@subtitles.command()
@click.argument("path")
@click.option("--recursive/--no-recursive", default=True, help="Process subdirectories")
@click.option("--language", "-l", multiple=True, help="Language codes")
@click.option("--output-dir", "-o", help="Output directory for subtitle files")
@click.option("--dry-run", is_flag=True, help="Preview what would be downloaded")
@click.option(
    "--skip-existing", is_flag=True, help="Skip videos that already have subtitles"
)
@click.pass_context
def batch(ctx, path, recursive, language, output_dir, dry_run, skip_existing):
    """Batch download subtitles for all videos in a directory"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            raise click.Abort()

        # Override languages if provided
        search_languages = list(language) if language else config.subtitles.languages

        # Scan for video files
        console.print(f"[bold blue]Scanning for video files in {path}...[/bold blue]")

        with NASClient(config) as nas_client:
            video_files = nas_client.scan_video_files(path, recursive)

        if not video_files:
            console.print("[yellow]No video files found[/yellow]")
            return

        console.print(f"Found {len(video_files)} video files")

        # Filter out files that already have subtitles if requested
        if skip_existing:
            analyzer = VideoAnalyzer(config)
            filtered_files = []
            for video_file in video_files:
                if not analyzer.should_skip_video(video_file.path):
                    filtered_files.append(video_file)

            video_files = filtered_files
            console.print(f"After filtering: {len(video_files)} files need subtitles")

        if not video_files:
            console.print("[green]All videos already have subtitles![/green]")
            return

        if dry_run:
            console.print("\n[bold]Would process these files:[/bold]")
            for video_file in video_files:
                console.print(f"  • {video_file.name} ({video_file.size_human})")
            return

        # Process files with progress tracking
        async def process_batch():
            service = SubtitleService(config)
            results = {"success": 0, "failed": 0, "skipped": 0}

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                main_task = progress.add_task(
                    "Processing videos...", total=len(video_files)
                )

                for i, video_file in enumerate(video_files):
                    current_desc = f"[{i + 1}/{len(video_files)}] {video_file.name}"
                    progress.update(main_task, description=current_desc)

                    try:
                        # Search for subtitles
                        subtitles = await service.search_for_video(
                            video_file.path, video_file.size
                        )

                        if not subtitles:
                            console.print(
                                f"[yellow]No subtitles found for {video_file.name}"
                                "[/yellow]"
                            )
                            results["skipped"] += 1
                            continue

                        # Download subtitles for each language
                        video_success = False
                        for lang in search_languages:
                            lang_subtitles = [
                                s for s in subtitles if s.language == lang
                            ]
                            if not lang_subtitles:
                                continue

                            best_subtitle = lang_subtitles[0]

                            # Generate output path
                            if output_dir:
                                output_path = Path(output_dir)
                            else:
                                output_path = Path(video_file.path).parent

                            subtitle_filename = service.generate_subtitle_filename(
                                video_file.name,
                                lang,
                                Path(best_subtitle.filename).suffix.lstrip("."),
                            )

                            full_output_path = output_path / subtitle_filename

                            success = await service.api.download_subtitle(
                                best_subtitle, full_output_path
                            )

                            if success:
                                video_success = True
                                console.print(
                                    f"[green]✓[/green] {video_file.name} ({lang})"
                                )

                        if video_success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1

                    except Exception as e:
                        console.print(f"[red]✗[/red] {video_file.name}: {e}")
                        results["failed"] += 1

                    progress.advance(main_task)

            return results

        console.print(
            f"\n[bold blue]Processing {len(video_files)} videos...[/bold blue]"
        )
        results = asyncio.run(process_batch())

        # Show summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"[green]✓ Success: {results['success']}[/green]")
        console.print(f"[red]✗ Failed: {results['failed']}[/red]")
        console.print(f"[yellow]- Skipped: {results['skipped']}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@subtitles.command()
@click.pass_context
def status(ctx):
    """Show subtitle download status and statistics"""
    console.print("[yellow]Feature not yet implemented[/yellow]")
    console.print("This will show download history and statistics in a future version")

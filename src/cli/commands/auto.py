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

from ...core.config import Config
from ...core.nas_client import NASClient
from ...core.subtitle_service import SubtitleService
from ...core.video_analyzer import VideoAnalyzer

console = Console()


@click.command()
@click.argument("path")
@click.option("--recursive/--no-recursive", default=True, help="Process subdirectories")
@click.option("--dry-run", is_flag=True, help="Preview what would be processed")
@click.option("--output-dir", "-o", help="Output directory for subtitle files")
@click.pass_context
def auto(ctx, path, recursive, dry_run, output_dir):
    """Automatically scan directory and download subtitles for all videos"""
    try:
        config = Config.load(ctx.obj.get("config_file"))
        errors = config.validate()
        if errors:
            console.print(
                "[red]Configuration errors found. Run 'config init' first.[/red]"
            )
            for error in errors:
                console.print(f"  • {error}")
            console.print("\nRun 'caption-mate config init' to set up configuration")
            raise click.Abort()

        console.print(f"[bold blue]Auto mode: Processing {path}[/bold blue]")
        console.print(f"Languages: {', '.join(config.subtitles.languages)}")
        console.print(f"Recursive: {'Yes' if recursive else 'No'}")
        console.print(
            f"Skip existing: {'Yes' if config.scanning.skip_existing else 'No'}"
        )

        # Step 1: Test NAS connection
        console.print("\n[bold]Step 1: Testing NAS connection...[/bold]")
        with console.status("[bold green]Connecting to NAS..."):
            with NASClient(config) as nas_client:
                if not nas_client.test_connection():
                    console.print("[red]✗ NAS connection failed[/red]")
                    raise click.Abort()

                console.print("[green]✓ NAS connection successful[/green]")

                # Verify path exists
                if not nas_client.path_exists(path):
                    console.print(f"[red]✗ Path does not exist: {path}[/red]")
                    raise click.Abort()

                console.print(f"[green]✓ Path exists: {path}[/green]")

        # Step 2: Scan for video files
        console.print("\n[bold]Step 2: Scanning for video files...[/bold]")
        with console.status(f"[bold green]Scanning {path}..."):
            with NASClient(config) as nas_client:
                video_files = nas_client.scan_video_files(path, recursive)

        if not video_files:
            console.print("[yellow]No video files found[/yellow]")
            return

        console.print(f"[green]✓ Found {len(video_files)} video files[/green]")

        # Step 3: Filter files that need subtitles
        if config.scanning.skip_existing:
            console.print("\n[bold]Step 3: Checking existing subtitles...[/bold]")
            analyzer = VideoAnalyzer(config)

            files_needing_subtitles = []
            files_with_subtitles = []

            for video_file in video_files:
                if analyzer.should_skip_video(video_file.path):
                    files_with_subtitles.append(video_file)
                else:
                    files_needing_subtitles.append(video_file)

            console.print(
                f"[green]✓ {len(files_with_subtitles)} files already have subtitles"
                "[/green]"
            )
            console.print(
                f"[yellow]• {len(files_needing_subtitles)} files need subtitles"
                "[/yellow]"
            )

            video_files = files_needing_subtitles

        if not video_files:
            console.print("\n[green]🎉 All videos already have subtitles![/green]")
            return

        # Show what will be processed
        if dry_run:
            console.print(
                f"\n[bold]Would process these {len(video_files)} files:[/bold]"
            )

            from rich.table import Table

            table = Table()
            table.add_column("File", style="cyan")
            table.add_column("Size", justify="right")
            table.add_column("Path", style="dim")

            for video_file in video_files[:30]:  # Show first 30
                table.add_row(video_file.name, video_file.size_human, video_file.path)

            if len(video_files) > 30:
                table.add_row("...", f"and {len(video_files) - 30} more", "...")

            console.print(table)

            # Estimate total size
            total_size = sum(f.size for f in video_files)
            size_gb = total_size / (1024**3)
            console.print(f"\nTotal video size: {size_gb:.1f} GB")

            return

        # Step 4: Download subtitles
        console.print(
            f"\n[bold]Step 4: Downloading subtitles for {len(video_files)} files..."
            "[/bold]"
        )

        async def process_all_videos():
            service = SubtitleService(config)
            results = {
                "total": len(video_files),
                "success": 0,
                "failed": 0,
                "no_subtitles": 0,
                "files_processed": [],
            }

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                main_task = progress.add_task(
                    "Downloading subtitles...", total=len(video_files)
                )

                for i, video_file in enumerate(video_files):
                    current_desc = f"Processing: {video_file.name}"
                    progress.update(main_task, description=current_desc)

                    file_result = {
                        "name": video_file.name,
                        "path": video_file.path,
                        "success": False,
                        "languages_downloaded": [],
                        "error": None,
                    }

                    try:
                        # Search for subtitles
                        subtitles = await service.search_for_video(
                            video_file.path, video_file.size
                        )

                        if not subtitles:
                            file_result["error"] = "No subtitles found"
                            results["no_subtitles"] += 1
                        else:
                            # Download subtitles for each configured language
                            languages_downloaded = []

                            for lang in config.subtitles.languages:
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

                                # Download
                                success = await service.api.download_subtitle(
                                    best_subtitle, full_output_path
                                )

                                if success:
                                    languages_downloaded.append(lang)

                            file_result["languages_downloaded"] = languages_downloaded

                            if languages_downloaded:
                                file_result["success"] = True
                                results["success"] += 1
                                console.print(
                                    f"[green]✓[/green] {video_file.name} "
                                    f"({', '.join(languages_downloaded)})"
                                )
                            else:
                                file_result[
                                    "error"
                                ] = "Download failed for all languages"
                                results["failed"] += 1
                                console.print(
                                    f"[red]✗[/red] {video_file.name}: Download failed"
                                )

                    except Exception as e:
                        file_result["error"] = str(e)
                        results["failed"] += 1
                        console.print(f"[red]✗[/red] {video_file.name}: {e}")

                    results["files_processed"].append(file_result)
                    progress.advance(main_task)

            return results

        # Run the batch processing
        results = asyncio.run(process_all_videos())

        # Show final summary
        console.print("\n[bold]🎬 Auto Processing Complete![/bold]")
        console.print(
            f"[green]✓ Success: {results['success']}/{results['total']} files[/green]"
        )
        console.print(
            f"[red]✗ Failed: {results['failed']}/{results['total']} files[/red]"
        )
        console.print(
            f"[yellow]- No subtitles found: {results['no_subtitles']}/"
            f"{results['total']} files[/yellow]"
        )

        # Show success rate
        if results["total"] > 0:
            success_rate = (results["success"] / results["total"]) * 100
            console.print(f"Success rate: {success_rate:.1f}%")

        # Show failed files if any
        failed_files = [f for f in results["files_processed"] if not f["success"]]
        if failed_files and len(failed_files) <= 10:
            console.print("\n[red]Failed files:[/red]")
            for failed_file in failed_files:
                error_msg = failed_file.get("error", "Unknown error")
                console.print(f"  • {failed_file['name']}: {error_msg}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

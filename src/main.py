import click
from dotenv import load_dotenv

from .cli.commands.config import config
from .cli.commands.nas import nas

load_dotenv()


@click.group()
@click.option(
    "--config-file",
    help="Specify custom config file path",
    envvar="CAPTION_MATE_CONFIG",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def main(ctx, config_file, verbose, quiet):
    """Caption-Mate: Intelligent subtitle matching for NAS videos"""
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# Register commands
main.add_command(config)
main.add_command(nas)


if __name__ == "__main__":
    main()

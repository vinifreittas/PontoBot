import importlib.metadata
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

import typer

# --- CONFIGURATION & CONSTANTS ---

GITHUB_REPO = "vinifreittas/PontoBot"
USER_AGENT = "PontoBotUpdateChecker/1.0"

cli = typer.Typer(
    name="pontobot",
    help="PontoBot - A Discord bot for checking presence",
    add_completion=False,
)


# --- UTILITY FUNCTIONS ---


def get_version() -> str:
    """Dynamically fetches the installed package version."""
    try:
        return importlib.metadata.version("pontobot")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.1 (local/dev)"


# --- COMMANDS ---


@cli.command()
def version() -> None:
    """Show the current program version."""
    typer.echo(f"PontoBot {get_version()}")


@cli.command()
def update() -> None:
    """Update the program to the latest version."""
    typer.echo("Checking for the latest version on GitHub...")
    current_ver = get_version()

    if "dev" in current_ver:
        typer.secho("You are running a local development version. Update skipped.", fg="yellow")
        return

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            latest_ver = data["tag_name"].lstrip("v")

    except urllib.error.URLError as e:
        typer.secho(f"Network error: Could not check for updates ({e.reason}).", fg="red")
        raise typer.Exit(code=1) from None

    except json.JSONDecodeError:
        typer.secho("Error: Failed to parse update response from GitHub.", fg="red")
        raise typer.Exit(code=1) from None

    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg="red")
        raise typer.Exit(code=1) from None

    if latest_ver == current_ver:
        typer.secho(f"You are already up to date! (v{current_ver})", fg="green")
        return

    typer.echo(f"A new version is available: v{latest_ver} (Current: v{current_ver})")
    if not typer.confirm("Would you like to update now?"):
        typer.echo("Update aborted.")
        return

    typer.echo("Updating PontoBot...")

    git_url = f"git+https://github.com/{GITHUB_REPO}.git"
    try:
        if shutil.which("uv"):
            typer.echo("Using 'uv' to upgrade...")
            command = ["uv", "pip", "install", "--upgrade", "--python", sys.executable, git_url]
        else:
            typer.echo("Using 'pip' to upgrade...")
            command = [sys.executable, "-m", "pip", "install", "--upgrade", git_url]

        subprocess.run(command, check=True)
        typer.secho("Successfully updated PontoBot!", fg="green")

    except subprocess.CalledProcessError:
        typer.secho("Update failed. Please run the upgrade command manually.", fg="red")


if __name__ == "__main__":
    cli()

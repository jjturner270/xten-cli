import typer
from xten.commands.compress import compress

__version__ = "0.1.0"

app = typer.Typer(help="xten — local-first media utility CLI")

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Show version"
    )
):
    if version:
        typer.echo(f"xten {__version__}")
        raise typer.Exit()


app.command(name="compress")(compress)

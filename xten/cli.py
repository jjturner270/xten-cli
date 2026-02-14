import typer
from xten.commands.compress import compress

app = typer.Typer(help="xten — local-first media utility CLI")

app.command()(compress)

if __name__ == "__main__":
    app()

from rich.console import Console
from rich.panel import Panel

console = Console()

def header(title: str):
    console.print(
        Panel.fit(
            f"[bold]xten[/bold] — {title}",
            border_style="white"
        )
    )

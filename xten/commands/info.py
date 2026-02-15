import typer
import subprocess
import json
import os
from xten.utils.console import header, console

def info(
    input_file: str,
    json_output: bool = typer.Option(
        False, "--json", help="Output raw JSON"
    )
):
    header("media info")

    if not os.path.exists(input_file):
        console.print("[red]Input file not found.[/red]")
        raise typer.Exit()

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        input_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        console.print("[red]ffprobe failed.[/red]")
        raise typer.Exit(code=1)

    if json_output:
        console.print_json(result.stdout)
        raise typer.Exit()

    data = json.loads(result.stdout)


    format_info = data.get("format", {})
    streams = data.get("streams", [])

    size_mb = int(format_info.get("size", 0)) / (1024 * 1024)
    duration = float(format_info.get("duration", 0))

    console.print()
    console.print(f"[bold]File:[/bold] {input_file}")
    console.print(f"[bold]Size:[/bold] {size_mb:.2f} MB")
    console.print(f"[bold]Duration:[/bold] {duration:.2f} sec")

    for stream in streams:
        codec_type = stream.get("codec_type")
        codec = stream.get("codec_name")

        if codec_type == "video":
            width = stream.get("width")
            height = stream.get("height")
            bitrate = stream.get("bit_rate")
            console.print(
                f"[bold]Video:[/bold] {codec} | {width}x{height}"
            )

        elif codec_type == "audio":
            bitrate = stream.get("bit_rate")
            console.print(
                f"[bold]Audio:[/bold] {codec}"
            )


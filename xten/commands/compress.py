import typer
import subprocess
import os
from xten.services.ffmpeg_service import get_duration
from xten.utils.console import header, console

def compress(
    input_file: str,
    target: str = typer.Option(..., help="Target file size (e.g. 8mb)")
):
    header("media compression")

    if not os.path.exists(input_file):
        console.print("[red]Input file not found.[/red]")
        raise typer.Exit()

    if not target.lower().endswith("mb"):
        console.print("[red]Target must be specified in MB (e.g. 8mb)[/red]")
        raise typer.Exit()

    target_mb = float(target.lower().replace("mb", ""))
    duration = get_duration(input_file)

    target_bits = target_mb * 8 * 1024 * 1024
    bitrate = int((target_bits / duration) * 0.95)

    output_file = f"{os.path.splitext(input_file)[0]}_xten.mp4"

    console.print(f"Input:   {input_file}")
    console.print(f"Target:  {target_mb} MB")
    console.print(f"Duration:{duration:.2f} sec")
    console.print(f"Bitrate: {bitrate} bps")

    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-b:v", str(bitrate),
        "-preset", "slow",
        "-movflags", "+faststart",
        output_file
    ]

    subprocess.run(cmd)

    console.print(f"[green]Done.[/green] Output: {output_file}")

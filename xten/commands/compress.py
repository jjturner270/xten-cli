import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

import typer
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from rich.prompt import Prompt

from xten.services.ffmpeg_service import get_duration
from xten.utils.console import header, console


# ============================================================
# Constants
# ============================================================

VALID_PRESETS = [
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]


# ============================================================
# Data Model
# ============================================================

@dataclass
class CompressionPlan:
    input_file: str
    output_file: str
    duration: float
    mode: str
    target_mb: Optional[float]
    video_bitrate: Optional[int]
    audio_bitrate: Optional[int]
    crf: Optional[int]
    preset: str
    command: list[str]


# ============================================================
# Helpers
# ============================================================

def resolve_output_name(base_path: str) -> str:
    if not os.path.exists(base_path):
        return base_path

    name, ext = os.path.splitext(base_path)
    counter = 1

    while True:
        candidate = f"{name}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


# ============================================================
# Interactive Input Collection
# ============================================================

def collect_compression_settings(
    target: Optional[str],
    crf: Optional[int],
    preset: Optional[str],
):
    if not target and crf is None:
        console.print()
        console.print("[bold]Choose compression mode:[/bold]")
        console.print("1) Target file size")
        console.print("2) CRF (quality mode)")
        console.print()

        choice = Prompt.ask("Select mode", choices=["1", "2"])

        if choice == "1":
            target = Prompt.ask("Enter target size (e.g. 8mb)")
        else:
            crf = int(Prompt.ask("Enter CRF value (18-28)", default="23"))

    if not preset:
        console.print()
        console.print("[bold]Encoding preset controls speed vs compression efficiency.[/bold]")
        console.print("Faster preset → quicker encode, larger file")
        console.print("Slower preset → slower encode, better compression")
        console.print()
        console.print("Recommended: [bold]slow[/bold] for quality balance")
        console.print()

        preset = Prompt.ask(
            "Select preset",
            choices=VALID_PRESETS,
            default="slow",
        )

    return target, crf, preset


# ============================================================
# Plan Builders
# ============================================================

def build_target_plan(
    input_file: str,
    target_mb: float,
    preset: str,
    force: bool,
) -> CompressionPlan:

    duration = get_duration(input_file)

    audio_bitrate = 128_000
    target_bits = target_mb * 8 * 1024 * 1024
    total_bitrate = int((target_bits / duration) * 0.95)
    video_bitrate = max(total_bitrate - audio_bitrate, 100_000)

    base_output = f"{os.path.splitext(input_file)[0]}_xten.mp4"
    output_file = base_output if force else resolve_output_name(base_output)

    cmd = ["ffmpeg"]

    if force:
        cmd.append("-y")

    cmd.extend([
        "-i", input_file,
        "-b:v", str(video_bitrate),
        "-b:a", str(audio_bitrate),
        "-preset", preset,
        "-movflags", "+faststart",
        output_file,
    ])

    return CompressionPlan(
        input_file=input_file,
        output_file=output_file,
        duration=duration,
        mode="target",
        target_mb=target_mb,
        video_bitrate=video_bitrate,
        audio_bitrate=audio_bitrate,
        crf=None,
        preset=preset,
        command=cmd,
    )


def build_crf_plan(
    input_file: str,
    crf: int,
    preset: str,
    force: bool,
) -> CompressionPlan:

    duration = get_duration(input_file)

    base_output = f"{os.path.splitext(input_file)[0]}_xten.mp4"
    output_file = base_output if force else resolve_output_name(base_output)

    cmd = ["ffmpeg"]

    if force:
        cmd.append("-y")

    cmd.extend([
        "-i", input_file,
        "-crf", str(crf),
        "-preset", preset,
        "-movflags", "+faststart",
        output_file,
    ])

    return CompressionPlan(
        input_file=input_file,
        output_file=output_file,
        duration=duration,
        mode="crf",
        target_mb=None,
        video_bitrate=None,
        audio_bitrate=None,
        crf=crf,
        preset=preset,
        command=cmd,
    )


# ============================================================
# Rendering
# ============================================================

def render_plan(plan: CompressionPlan):
    console.print()
    console.print(f"[bold]Input:[/bold] {plan.input_file}")
    console.print(f"[bold]Output:[/bold] {plan.output_file}")
    console.print(f"[bold]Preset:[/bold] {plan.preset}")
    console.print(f"[bold]Duration:[/bold] {plan.duration:.2f} sec")

    if plan.mode == "target":
        console.print(f"[bold]Target:[/bold] {plan.target_mb} MB")
        console.print(
            f"[bold]Video Bitrate:[/bold] {plan.video_bitrate // 1000} kbps"
        )
        console.print(
            f"[bold]Audio Bitrate:[/bold] {plan.audio_bitrate // 1000} kbps"
        )
    else:
        console.print(f"[bold]CRF:[/bold] {plan.crf}")

    console.print()


# ============================================================
# Execution
# ============================================================

def execute_plan(plan: CompressionPlan):
    process = subprocess.Popen(
        plan.command,
        stderr=subprocess.PIPE,
        text=True,
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
    ) as progress:

        task = progress.add_task("Encoding", total=plan.duration)

        for line in process.stderr:
            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                current_time = hours * 3600 + minutes * 60 + seconds
                progress.update(task, completed=current_time)

        process.wait()

    if process.returncode != 0:
        console.print("[red]ffmpeg failed.[/red]")
        raise typer.Exit(code=1)

    output_size = os.path.getsize(plan.output_file) / (1024 * 1024)

    console.print()
    console.print(f"[bold]Final Size:[/bold] {output_size:.2f} MB")
    console.print("[green]Done.[/green]")


# ============================================================
# CLI Entry
# ============================================================

def compress(
    input_file: str,
    target: str = typer.Option(None, help="Target file size (e.g. 8mb)"),
    crf: int = typer.Option(None, help="CRF quality mode (18-28)"),
    preset: str = typer.Option(None, help="Encoding preset"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
):
    header("media compression")

    if not os.path.exists(input_file):
        console.print("[red]Input file not found.[/red]")
        raise typer.Exit(code=1)

    if not shutil.which("ffmpeg"):
        console.print("[red]ffmpeg not found in PATH.[/red]")
        raise typer.Exit(code=1)

    target, crf, preset = collect_compression_settings(target, crf, preset)

    if preset not in VALID_PRESETS:
        console.print("[red]Invalid preset.[/red]")
        raise typer.Exit(code=1)

    if target:
        if not target.lower().endswith("mb"):
            console.print("[red]Target must be specified in MB (e.g. 8mb).[/red]")
            raise typer.Exit(code=1)

        target_mb = float(target.lower().replace("mb", ""))
        plan = build_target_plan(input_file, target_mb, preset, force)
    else:
        plan = build_crf_plan(input_file, crf, preset, force)

    render_plan(plan)

    if dry_run:
        console.print("[yellow]Dry run mode — no encoding performed.[/yellow]")
        console.print()
        console.print("[bold]Command Preview:[/bold]")
        console.print(" ".join(plan.command))
        raise typer.Exit()

    execute_plan(plan)

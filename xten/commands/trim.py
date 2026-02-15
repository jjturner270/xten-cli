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
# Data Model
# ============================================================

@dataclass
class TrimPlan:
    input_file: str
    output_file: str
    duration: float
    start: str
    end: str
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


def normalize_time_label(t: str) -> str:
    """
    Accepts:
      - "12" (seconds)
      - "12.5"
      - "00:12"
      - "01:02:03.5"
    Returns a string ffmpeg will accept.
    """
    t = t.strip()
    if not t:
        raise ValueError("Empty time")

    # If it's purely numeric, treat as seconds
    try:
        float(t)
        return t
    except ValueError:
        pass

    # Otherwise accept as HH:MM:SS(.ms) or MM:SS(.ms)
    # ffmpeg is fairly permissive, so we just do a light sanity check.
    if ":" not in t:
        raise ValueError(f"Invalid time format: {t}")

    return t


def hhmmss_from_seconds(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def parse_ffmpeg_time_to_seconds(line: str) -> Optional[float]:
    """
    Parses ffmpeg stderr lines containing: time=HH:MM:SS.xx
    Returns seconds if found.
    """
    match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


# ============================================================
# Interactive Input Collection
# ============================================================

def collect_trim_settings(
    duration: float,
    start: Optional[str],
    end: Optional[str],
):
    console.print()
    console.print(f"[bold]Duration:[/bold] {duration:.2f} sec ({hhmmss_from_seconds(duration)})")
    console.print()

    if not start:
        start = Prompt.ask("Start time (seconds or HH:MM:SS)", default="0")

    if not end:
        end = Prompt.ask(
            "End time (seconds or HH:MM:SS)",
            default=f"{duration:.2f}"
        )

    # Normalize for ffmpeg acceptance
    start_norm = normalize_time_label(start)
    end_norm = normalize_time_label(end)

    return start_norm, end_norm


# ============================================================
# Plan Builder
# ============================================================

def build_trim_plan(
    input_file: str,
    start: str,
    end: str,
    force: bool,
) -> TrimPlan:
    duration = get_duration(input_file)

    base_output = f"{os.path.splitext(input_file)[0]}_xten_trim.mp4"
    output_file = base_output if force else resolve_output_name(base_output)

    # Fast/lossless trim: stream copy
    # Place -ss before -i for faster seeking; for copy trims this is typically fine.
    cmd = ["ffmpeg"]

    if force:
        cmd.append("-y")

    cmd.extend([
        "-ss", start,
        "-to", end,
        "-i", input_file,
        "-c", "copy",
        "-movflags", "+faststart",
        output_file,
    ])

    return TrimPlan(
        input_file=input_file,
        output_file=output_file,
        duration=duration,
        start=start,
        end=end,
        command=cmd,
    )


# ============================================================
# Rendering
# ============================================================

def render_plan(plan: TrimPlan):
    console.print()
    console.print(f"[bold]Input:[/bold]  {plan.input_file}")
    console.print(f"[bold]Output:[/bold] {plan.output_file}")
    console.print(f"[bold]Start:[/bold]  {plan.start}")
    console.print(f"[bold]End:[/bold]    {plan.end}")
    console.print()


# ============================================================
# Execution
# ============================================================

def execute_plan(plan: TrimPlan):
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

        # We don't know trimmed duration reliably without parsing start/end into seconds,
        # so we show progress across the full input duration (still useful feedback).
        task = progress.add_task("Trimming", total=plan.duration)

        for line in process.stderr:
            t = parse_ffmpeg_time_to_seconds(line)
            if t is not None:
                progress.update(task, completed=min(t, plan.duration))

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

def trim(
    input_file: str,
    start: str = typer.Option(None, help="Start time (seconds or HH:MM:SS[.ms])"),
    end: str = typer.Option(None, help="End time (seconds or HH:MM:SS[.ms])"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
):
    header("media trim")

    if not os.path.exists(input_file):
        console.print("[red]Input file not found.[/red]")
        raise typer.Exit(code=1)

    if not shutil.which("ffmpeg"):
        console.print("[red]ffmpeg not found in PATH.[/red]")
        raise typer.Exit(code=1)

    duration = get_duration(input_file)

    start, end = collect_trim_settings(duration, start, end)

    plan = build_trim_plan(input_file, start, end, force)

    render_plan(plan)

    if dry_run:
        console.print("[yellow]Dry run mode — no trimming performed.[/yellow]")
        console.print()
        console.print("[bold]Command Preview:[/bold]")
        console.print(" ".join(plan.command))
        raise typer.Exit()

    execute_plan(plan)

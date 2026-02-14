import subprocess
import json

def get_duration(file_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    return float(data["format"]["duration"])

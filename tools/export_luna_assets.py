"""Build transparent desktop frames from the frozen Luna Godot project.

This is an asset build, not a desktop-pet launch or a UI test. The original
Luna_Final directory is only read. Godot imports and renders an isolated copy
under build/luna_export with its window hidden and outside the desktop.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Luna_Final"
STAGING = ROOT / "build" / "luna_export"
OUTPUT = ROOT / "assets" / "luna"
FRAMES = STAGING / "frames"
ENGINE_NAME = "Godot_v4.7.2-stable_win64.exe"
RESOURCE_DIRS = (
    "animations", "assets", "controllers", "data", "effects",
    "runtime_layers", "states",
)


def prepare() -> Path:
    """Copy production resources; never import or change the frozen source."""
    STAGING.mkdir(parents=True, exist_ok=True)
    for name in RESOURCE_DIRS:
        shutil.copytree(
            SOURCE / name, STAGING / name, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.import", "__pycache__"),
        )
    (STAGING / "scripts").mkdir(exist_ok=True)
    for name in ("luna_pet.gd", "luna_rig.gd"):
        shutil.copy2(SOURCE / "scripts" / name, STAGING / "scripts" / name)
    for name in ("LunaPet.tscn", "LunaRig.tscn"):
        shutil.copy2(SOURCE / name, STAGING / name)
    shutil.copy2(ROOT / "tools" / "luna_export.gd", STAGING / "luna_export.gd")
    # Apply the desktop greeting without editing the frozen animation project.
    shutil.copy2(ROOT / "tools" / "luna_attention.gd", STAGING / "states" / "attention.gd")
    engine_dir = STAGING / "engine"
    engine_dir.mkdir(exist_ok=True)
    # Self-contained editor data lives in staging, never beside the source exe.
    for name in (ENGINE_NAME, "LICENSE.md", "_sc_"):
        source = SOURCE / "tools" / "godot" / name
        target = engine_dir / name
        if not target.exists() or source.stat().st_mtime_ns != target.stat().st_mtime_ns:
            shutil.copy2(source, target)
    (engine_dir / ".gdignore").touch()
    (STAGING / "project.godot").write_text(
        'config_version=5\n[application]\nconfig/name="Luna Asset Export"\n'
        '[display]\nwindow/size/viewport_width=384\n'
        'window/size/viewport_height=576\nwindow/size/borderless=true\n'
        'window/size/initial_position_type=0\n'
        'window/size/initial_position=Vector2i(-32000, -32000)\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\n'
        'renderer/rendering_method.mobile="gl_compatibility"\n'
        'textures/default_filters/use_nearest_mipmap_filter=false\n'
        'environment/defaults/default_clear_color=Color(0,0,0,0)\n'
        '[debug]\nfile_logging/enable_file_logging=false\n',
        encoding="utf-8",
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    (FRAMES / ".gdignore").touch()
    return engine_dir / ENGINE_NAME


def replace_completed_file(source: Path, target: Path) -> None:
    """Allow a Windows image reader or scanner to finish its brief file access."""
    deadline = time.monotonic() + 3.0
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def publish(*, only_attention: bool = False) -> dict:
    """Publish complete files, then the manifest; never expose half a PNG."""
    manifest = json.loads((FRAMES / "manifest.json").read_text(encoding="utf-8"))
    current_path = OUTPUT / "manifest.json"
    previous = json.loads(current_path.read_text(encoding="utf-8")) if current_path.exists() else {"clips": {}}
    filenames = {name for clip in manifest["clips"].values() for name in clip["frames"]}
    for name in sorted(filenames):
        if only_attention and not name.startswith("attention_"):
            continue
        source, target = FRAMES / name, OUTPUT / name
        source.resolve().relative_to(FRAMES.resolve())
        target.resolve().relative_to(OUTPUT.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".png.build")
        shutil.copy2(source, temporary)
        replace_completed_file(temporary, target)
    temporary_manifest = current_path.with_suffix(".json.build")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    replace_completed_file(temporary_manifest, current_path)
    # Only remove retired, generated PNGs listed by the previous manifest.
    # No directory traversal or recursive deletion, and no source assets.
    retired = {name for clip in previous["clips"].values() for name in clip["frames"]} - filenames
    for name in retired:
        path = (OUTPUT / name).resolve()
        path.relative_to(OUTPUT.resolve())
        if path.suffix == ".png":
            path.unlink(missing_ok=True)
    return manifest


def _ps_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def run_hidden(engine: Path, arguments: list[str], name: str, timeout: int) -> None:
    """Start Windows Godot hidden, collect logs, and bound a stuck renderer."""
    if os.name != "nt":
        raise RuntimeError("The bundled asset builder requires Windows.")
    stdout = STAGING / f"{name}.log"
    stderr = STAGING / f"{name}.err.log"
    stdout.unlink(missing_ok=True)
    stderr.unlink(missing_ok=True)
    command_line = subprocess.list2cmdline(arguments)
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$process=Start-Process -FilePath {_ps_literal(engine)} "
        f"-ArgumentList {_ps_literal(command_line)} "
        f"-WorkingDirectory {_ps_literal(STAGING)} -WindowStyle Hidden "
        f"-RedirectStandardOutput {_ps_literal(stdout)} "
        f"-RedirectStandardError {_ps_literal(stderr)} -PassThru; "
        f"if (-not $process.WaitForExit({timeout * 1000})) {{ "
        "Stop-Process -Id $process.Id -Force; throw 'Godot asset build timed out' }; "
        "$process.Refresh(); Write-Output ('Godot process exit: ' + $process.ExitCode); exit $process.ExitCode"
    )
    process = subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    offset = 0
    while process.poll() is None:
        if stdout.exists():
            with stdout.open("r", encoding="utf-8", errors="replace") as log:
                log.seek(offset)
                chunk = log.read()
                offset = log.tell()
            if chunk:
                print(chunk, end="", flush=True)
        time.sleep(0.25)
    if stdout.exists():
        with stdout.open("r", encoding="utf-8", errors="replace") as log:
            log.seek(offset)
            print(log.read(), end="", flush=True)
    errors = stderr.read_text(encoding="utf-8", errors="replace") if stderr.exists() else ""
    if errors:
        print(errors, flush=True)
    # Certificate lookup is unrelated to this offline render; the restricted
    # build environment may deny it even when the engine exits successfully.
    actionable = "\n".join(line for line in errors.splitlines()
                           if "Failed to read the root certificate store." not in line
                           and "Could not open 'user://' directory" not in line)
    if process.returncode or "SCRIPT ERROR" in actionable or "ERROR:" in actionable:
        raise RuntimeError(f"Godot {name} failed (launcher exit {process.returncode}); see {stdout} and {stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--only-attention", action="store_true",
                        help="Rebuild only the desktop greeting; keep all other clips.")
    args = parser.parse_args()
    engine = prepare()
    print(f"Isolated production resources: {STAGING}", flush=True)
    if args.prepare_only:
        return
    if not args.skip_import:
        run_hidden(engine, ["--headless", "--path", str(STAGING), "--editor", "--import", "--quit"], "import", 240)
    if args.only_attention:
        shutil.copy2(OUTPUT / "manifest.json", FRAMES / "manifest.json")
    render_arguments = ["--path", str(STAGING), "--position", "-32000,-32000",
                        "--resolution", "384x576", "--disable-vsync", "--max-fps", "0",
                        "--script", "res://luna_export.gd", "--", str(FRAMES)]
    if args.only_attention:
        render_arguments.append("attention")
    run_hidden(
        engine,
        render_arguments,
        "render", 900,
    )
    manifest = publish(only_attention=args.only_attention)
    print(f"Built {len(manifest['clips'])} clips in {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()

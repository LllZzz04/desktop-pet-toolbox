"""Local files, atomic JSON writes, and bounded rotating logs."""
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QStandardPaths


def data_directory() -> Path:
    override = os.environ.get("DESKTOP_PET_DATA_DIR")
    path = Path(override) if override else Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        logging.exception("Cannot read %s", path)
        # Retain the invalid file for recovery before a future write.
        try:
            path.replace(path.with_suffix(path.suffix + ".broken"))
        except OSError:
            logging.exception("Cannot preserve damaged file")
        return default


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def setup_logging(directory: Path):
    handler = RotatingFileHandler(directory / "app.log", maxBytes=1_000_000,
                                  backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

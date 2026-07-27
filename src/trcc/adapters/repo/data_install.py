"""Data-archive installer — port of legacy ``DataManager``.

Per resolution: three archives on the project GitHub — stock themes,
cloud preview thumbnails, and cloud masks.  Non-square devices (e.g.
1600×720) additionally fetch the rotated counterpart's web + masks
(720×1600), so a portrait rotation immediately shows local content
without a re-download.  Without these the GUI's theme browser, web
preview grid, and mask grid are all empty on first run.

Layout under ``paths.data_dir()`` matches legacy byte-for-byte so this
port reads existing content in place:

    theme{w}{h}/         stock themes for {w}×{h}
    web/{w}{h}/          cloud-catalog preview thumbnails
    web/zt{w}{h}/        cloud-catalog masks
    (plus rotated web/{h}{w}/ and web/zt{h}{w}/ when w ≠ h)

Source-of-truth: the same archives the legacy installer used —
``raw.githubusercontent.com/Lexonight1/thermalright-trcc-linux/main/
src/trcc/data/{subpath}/{archive}.7z``.

7z extraction goes through the system ``7z`` binary; ``Platform``
provides the per-OS install hint.  If ``7z`` isn't on PATH the
installer logs a warning and skips extraction (theme browser stays
empty, but the app keeps running).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from ...core._safe import is_safe_zip_member
from ...core.errors import HttpFetchError, TrccError
from ...core.ports import DataInstaller, HttpFetcher

log = logging.getLogger(__name__)


_GITHUB_BASE = (
    "https://raw.githubusercontent.com/Lexonight1/"
    "thermalright-trcc-linux/main/src/trcc/data/"
)


# Hide the console window on Windows when shelling out to 7z (parity
# with the legacy installer's ``CREATE_NO_WINDOW`` flag).
_NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class _ArchiveExtractor(Protocol):
    """Pluggable extractor seam — production uses 7z CLI, tests fake it."""
    def extract(self, archive: Path, target: Path) -> bool: ...


class SevenZipExtractor:
    """7z CLI wrapper with zip-slip guard.

    Lists the archive first, rejects members that escape ``target``,
    then extracts.  Returns ``False`` (with a warning) if 7z is missing
    or extraction fails — caller stays alive and the GUI just shows an
    empty grid for that resolution.
    """

    __slots__ = ()

    def extract(self, archive: Path, target: Path) -> bool:
        target.mkdir(parents=True, exist_ok=True)
        try:
            listing = subprocess.run(
                ["7z", "l", "-slt", str(archive)],
                capture_output=True, text=True, timeout=30,
                creationflags=_NO_WINDOW,
            )
        except FileNotFoundError:
            log.warning(
                "7z not on PATH — cannot extract %s.  Install p7zip / 7-Zip "
                "to populate the theme browser.",
                archive.name,
            )
            return False
        except (OSError, subprocess.SubprocessError) as e:
            log.warning("7z listing failed for %s: %s: %s",
                        archive.name, type(e).__name__, e)
            return False
        if listing.returncode != 0:
            log.warning("7z listing rc=%d: %s",
                        listing.returncode, listing.stderr.strip())
            return False
        archive_norm = os.path.normpath(str(archive))
        for line in listing.stdout.splitlines():
            if not line.startswith("Path = "):
                continue
            member = line[len("Path = "):]
            if os.path.normpath(member) == archive_norm:
                continue
            if not is_safe_zip_member(member):
                log.warning("Blocked unsafe archive member: %s", member)
                return False
        try:
            result = subprocess.run(
                ["7z", "x", str(archive), f"-o{target}", "-y"],
                capture_output=True, timeout=120,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as e:
            log.warning("7z extraction failed for %s: %s: %s",
                        archive.name, type(e).__name__, e)
            return False
        if result.returncode == 0:
            log.info("extracted %s", archive.name)
            return True
        log.warning("7z extraction rc=%d: %s",
                    result.returncode,
                    result.stderr.decode(errors="replace"))
        return False


# =========================================================================
# HttpDataInstaller — concrete DataInstaller port, DI'd into the service layer
# =========================================================================


class HttpDataInstaller(DataInstaller):
    """Downloads + extracts per-resolution archives from GitHub.

    Construct with an ``HttpFetcher`` (the existing adapter from
    ``adapters.repo.http``) and an optional ``_ArchiveExtractor``.
    Default extractor shells out to the system ``7z`` binary.
    """

    __slots__ = ("_extractor", "_http")

    def __init__(
        self,
        http: HttpFetcher,
        *,
        extractor: _ArchiveExtractor | None = None,
    ) -> None:
        self._http = http
        self._extractor = extractor or SevenZipExtractor()

    def install(
        self,
        archive_name: str,
        target_dir: Path,
        *,
        subpath: str = "",
    ) -> bool:
        """Fetch ``archive_name`` from GitHub and extract into ``target_dir``.

        ``subpath`` is the directory under ``src/trcc/data/`` where the
        archive lives on GitHub — ``""`` for stock themes, ``"web"``
        for cloud previews + masks.  Returns ``True`` if the target
        ends up populated (download or already extracted).
        """
        if _is_populated(target_dir):
            log.debug("install: %s already populated at %s",
                      archive_name, target_dir)
            return True

        # Bundled-data fallback: if the data ships pre-extracted next to
        # the exe (portable layout) or in PyInstaller's _internal/trcc/data/,
        # seed the target from there before hitting GitHub.  Makes the app
        # fully offline-capable when themes/videos/masks are bundled.
        if _seed_from_bundle(target_dir, subpath):
            log.info("install: %s seeded from bundled data at %s",
                     archive_name, target_dir)
            return True

        # Local 7z archive fallback: if the .7z archive exists in the
        # bundled data directory (shipped via PyInstaller datas), extract
        # it locally instead of downloading from GitHub.
        if _extract_local_archive(archive_name, target_dir, subpath, self._extractor):
            log.info("install: %s extracted from local archive at %s",
                     archive_name, target_dir)
            return True

        url_subpath = f"{subpath}/" if subpath else ""
        url = f"{_GITHUB_BASE}{url_subpath}{archive_name}"
        archive_tmp = target_dir.parent / f"{archive_name}.tmp"

        log.info("install: fetching %s from GitHub", archive_name)
        try:
            data = self._http.fetch(url, timeout_s=120.0)
        except HttpFetchError as e:
            log.warning("install: %s download failed: %s",
                        archive_name, e)
            return False

        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            archive_tmp.write_bytes(data)
        except OSError as e:
            log.warning("install: cannot stage %s: %s: %s",
                        archive_tmp, type(e).__name__, e)
            return False

        try:
            ok = self._extractor.extract(archive_tmp, target_dir)
        finally:
            try:
                archive_tmp.unlink(missing_ok=True)
            except OSError:
                pass

        if ok:
            _unwrap_nested_dir(target_dir)
            log.info("install: %s ready at %s", archive_name, target_dir)
        return ok


def _is_populated(directory: Path) -> bool:
    """A target dir is "ready" if it contains at least one regular file
    or subdirectory.  Tracks the same semantics as legacy ``has_themes``
    (which checked for any subdir or theme file)."""
    try:
        return directory.is_dir() and any(directory.iterdir())
    except OSError:
        return False


def _seed_from_bundle(target_dir: Path, subpath: str) -> bool:
    """Copy pre-extracted data from a bundled location into ``target_dir``.

    Looks for the data in two places (in order):
      1. ``<exe_dir>/_internal/trcc/data/`` — PyInstaller onedir bundle.
      2. ``<exe_dir>/data/`` — portable folder layout next to the exe.

    ``subpath`` is ``""`` for stock themes (matches ``theme{w}{h}/`` dirs
    at the data root) or ``"web"`` for cloud previews + masks (matches
    ``web/{w}{h}/`` and ``web/zt{w}{h}/`` under the data root).

    Returns ``True`` if the target ends up populated.  Best-effort —
    logs a warning on copy failure and returns ``False`` so the caller
    falls back to the GitHub download path.
    """
    import sys
    exe_dir = Path(sys.executable).parent
    candidates = [
        exe_dir / "_internal" / "trcc" / "data",
        exe_dir / "data",
    ]
    # The target's leaf name (e.g. ``theme4621920`` or ``zt480480``)
    # identifies the specific resolution folder to seed.
    leaf = target_dir.name
    for bundle_root in candidates:
        if not bundle_root.is_dir():
            continue
        if subpath:
            # Cloud previews/masks live under ``web/`` in the bundle.
            src = bundle_root / subpath / leaf
        else:
            # Stock themes live at the bundle root directly.
            src = bundle_root / leaf
        if not src.is_dir() or not any(src.iterdir()):
            continue
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(src), str(target_dir), dirs_exist_ok=True)
            log.info("seed: copied %s -> %s", src, target_dir)
            return True
        except OSError as e:
            log.warning("seed: copy failed %s -> %s: %s: %s",
                        src, target_dir, type(e).__name__, e)
            return False
    return False


def _extract_local_archive(
    archive_name: str,
    target_dir: Path,
    subpath: str,
    extractor: _ArchiveExtractor,
) -> bool:
    """Extract a local .7z archive from bundled data into ``target_dir``.

    Searches for ``archive_name`` (e.g. ``1920400.7z``) in the same
    bundled data directories as ``_seed_from_bundle`` — PyInstaller's
    ``_internal/trcc/data/`` and ``<exe>/data/``.  When the archive
    exists, extracts it with the 7z CLI extractor.

    Returns ``True`` if the target ends up populated.
    """
    import sys
    exe_dir = Path(sys.executable).parent
    candidates = [
        exe_dir / "_internal" / "trcc" / "data",
        exe_dir / "data",
    ]
    for bundle_root in candidates:
        if not bundle_root.is_dir():
            continue
        archive_path = bundle_root / subpath / archive_name if subpath else bundle_root / archive_name
        if not archive_path.is_file():
            continue
        log.info("extract_local: found %s in bundled data", archive_path)
        ok = extractor.extract(archive_path, target_dir)
        if ok:
            _unwrap_nested_dir(target_dir)
            return True
    return False


def _unwrap_nested_dir(target_dir: Path) -> None:
    """Flatten single-wrapping subdirectories — some archives wrap
    contents in a subdirectory matching the archive name.  Matches
    legacy ``DataManager._unwrap_nested_dir`` semantics."""
    try:
        entries = list(target_dir.iterdir())
    except OSError:
        return
    if len(entries) != 1:
        return
    nested = entries[0]
    if not nested.is_dir():
        return
    log.debug("unwrapping nested directory: %s", nested)
    for item in nested.iterdir():
        dst = target_dir / item.name
        shutil.move(str(item), str(dst))
    try:
        nested.rmdir()
    except OSError as e:
        log.warning("unwrap: cannot remove %s: %s", nested, e)


class DataInstallError(TrccError):
    """Raised when no archive can be obtained AND no local data exists."""

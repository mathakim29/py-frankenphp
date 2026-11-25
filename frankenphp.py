from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import urllib.request

REPO = "php/frankenphp"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
CACHE_ROOT = Path.home() / ".cache" / "frankenphp-cli"


def _asset_name() -> str:
    os_name = platform.system().lower()
    arch_raw = platform.machine().lower()

    if arch_raw in ("x86_64", "amd64"):
        arch = "x86_64"
    elif arch_raw in ("aarch64", "arm64"):
        arch = "aarch64" if os_name == "linux" else "arm64"
    else:
        raise SystemExit(f"Unsupported architecture: {arch_raw}")

    if os_name == "linux":
        return f"frankenphp-linux-{arch}"
    if os_name == "darwin":
        return f"frankenphp-mac-{arch}"
    if os_name == "windows":
        return f"frankenphp-windows-{arch}.exe"
    raise SystemExit(f"Unsupported operating system: {os_name}")


def _latest_asset_url(asset_name: str) -> tuple[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "frankenphp-cli"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(LATEST_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    tag = data.get("tag_name", "latest")
    for asset in data.get("assets", []):
        if asset.get("name") == asset_name:
            return tag, asset["browser_download_url"]

    raise SystemExit(f"Asset '{asset_name}' not found in release {tag}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "frankenphp-cli"})
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        while chunk := resp.read(65536):
            out.write(chunk)
    tmp.replace(dest)
    if os.name != "nt":
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    asset = _asset_name()
    tag, url = _latest_asset_url(asset)
    binary = CACHE_ROOT / tag / asset

    if not binary.exists():
        _download(url, binary)

    completed = subprocess.run([str(binary), *sys.argv[1:]])
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Copy the packaged simple-site assets into one Umbraco web project."""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS = SKILL_DIR / "assets"
VIEW_NAMES = ("HomePage.cshtml", "ContentPage.cshtml")
SKIP_DIRS = {".git", ".aspire", "bin", "obj", "node_modules", "dist"}


class CopyError(Exception):
    pass


def is_umbraco_project(project: Path) -> bool:
    try:
        root = ElementTree.parse(project).getroot()
    except (ElementTree.ParseError, OSError):
        return False
    return any(
        element.tag.rsplit("}", 1)[-1] == "PackageReference"
        and element.attrib.get("Include") == "Umbraco.Cms"
        for element in root.iter()
    )


def immediate_projects(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("*.csproj") if is_umbraco_project(path))


def descendant_projects(directory: Path) -> list[Path]:
    projects = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith(".")]
        for name in files:
            if name.endswith(".csproj"):
                project = Path(root) / name
                if is_umbraco_project(project):
                    projects.append(project)
    return sorted(projects)


def choose_one(projects: list[Path], location: Path) -> Path:
    if len(projects) == 1:
        return projects[0]
    if not projects:
        raise CopyError(f"No Umbraco.Cms web project found in {location}.")
    options = "\n  ".join(str(project) for project in projects)
    raise CopyError(f"Multiple Umbraco projects found; pass the intended folder or .csproj:\n  {options}")


def resolve_project(target: Path | None) -> Path:
    if target is not None:
        target = target.expanduser().resolve()
        if target.is_file():
            if target.suffix != ".csproj" or not is_umbraco_project(target):
                raise CopyError(f"Not an Umbraco.Cms web project: {target}")
            return target
        if not target.is_dir():
            raise CopyError(f"Target does not exist: {target}")
        nearby = immediate_projects(target)
        return choose_one(nearby or descendant_projects(target), target)

    cwd = Path.cwd().resolve()
    for directory in (cwd, *cwd.parents):
        nearby = immediate_projects(directory)
        if nearby:
            return choose_one(nearby, directory)
    return choose_one(descendant_projects(cwd), cwd)


def copy_assets(project: Path, overwrite: bool) -> None:
    source_usync = ASSETS / "uSync"
    source_views = ASSETS / "Views"
    if not source_usync.is_dir() or any(not (source_views / name).is_file() for name in VIEW_NAMES):
        raise CopyError(f"Skill assets are incomplete in {ASSETS}.")

    project_dir = project.parent
    existing_usync = [path for path in project_dir.iterdir() if path.name.casefold() == "usync"]
    if len(existing_usync) > 1:
        raise CopyError(f"Multiple uSync folders exist in {project_dir}; resolve them before copying.")
    if existing_usync and (existing_usync[0].is_symlink() or not existing_usync[0].is_dir()):
        raise CopyError(f"Existing uSync path is not a regular directory: {existing_usync[0]}")

    views_dir = project_dir / "Views"
    if views_dir.is_symlink() or (views_dir.exists() and not views_dir.is_dir()):
        raise CopyError(f"Views path is not a regular directory: {views_dir}")
    view_destinations = [views_dir / name for name in VIEW_NAMES]
    if any(path.is_symlink() or (path.exists() and not path.is_file()) for path in view_destinations):
        raise CopyError("A target view path is a symlink or is not a regular file.")

    collisions = existing_usync + [path for path in view_destinations if path.exists()]
    if collisions and not overwrite:
        paths = "\n  ".join(str(path) for path in collisions)
        raise CopyError(f"Existing assets would be replaced; rerun with --overwrite to replace them:\n  {paths}")

    with tempfile.TemporaryDirectory(prefix=".umbraco-simple-site-", dir=project_dir) as temp_name:
        temp = Path(temp_name)
        staged_usync = temp / "new-uSync"
        staged_views = temp / "new-Views"
        shutil.copytree(source_usync, staged_usync)
        staged_views.mkdir()
        for name in VIEW_NAMES:
            shutil.copy2(source_views / name, staged_views / name)

        operations = [(existing_usync[0] if existing_usync else None, project_dir / "uSync", staged_usync)]
        operations += [(dest if dest.exists() else None, dest, staged_views / dest.name) for dest in view_destinations]
        backups: list[tuple[Path, Path]] = []
        installed: list[Path] = []
        created_views = not views_dir.exists()
        try:
            views_dir.mkdir(exist_ok=True)
            for index, (existing, destination, staged) in enumerate(operations):
                if existing is not None:
                    backup = temp / f"backup-{index}"
                    os.replace(existing, backup)
                    backups.append((backup, existing))
                os.replace(staged, destination)
                installed.append(destination)
        except OSError:
            for destination in reversed(installed):
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            for backup, original in reversed(backups):
                os.replace(backup, original)
            if created_views:
                views_dir.rmdir()
            raise

    print(f"Copied simple-site uSync assets and two views to {project_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, help="Umbraco web project folder or .csproj")
    parser.add_argument("--overwrite", action="store_true", help="Replace the existing uSync folder and packaged views")
    args = parser.parse_args()
    try:
        copy_assets(resolve_project(args.target), args.overwrite)
    except (CopyError, OSError) as error:
        print(f"umbraco-simple-site: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import time
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

from map_gen.renderer import draw_metro_map

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = ROOT_DIR / "library" / "gz"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "map_preview.png"
DEFAULT_PACK_OUTPUT = ROOT_DIR / "map_package.zip"
DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/TTF/Comfortaa.ttf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
]

Renderer = Callable[[dict[str, Any], str, str | None, list[str] | None], None]
SvgPngConverter = Callable[[Path, Path], None]
SleepFunc = Callable[[float], None]
RenderFunc = Callable[
    [Path, Path, Path | None, Sequence[str] | None, float, str, Renderer],
    bool,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mapro CLI tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser(
        "render",
        help="Render a metro map preview image",
    )
    render_parser.add_argument(
        "data",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to the metro map data JSON file",
    )
    render_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the generated preview image",
    )
    render_parser.add_argument(
        "--background",
        type=Path,
        default=None,
        help="Optional background image path",
    )
    render_parser.add_argument(
        "--font",
        action="append",
        dest="fonts",
        default=None,
        help="Additional font path, can be passed multiple times",
    )
    render_parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale station coordinates before rendering",
    )
    render_parser.add_argument(
        "--mode",
        choices=("pil", "svg", "svg-png"),
        default="pil",
        help="Rendering backend: pil image, svg vector, or SVG converted to PNG",
    )
    render_parser.add_argument(
        "--preview",
        action="store_true",
        help="Fast preview: clamp the longest output edge to 1600px",
    )
    render_parser.add_argument(
        "--no-badges",
        dest="badges",
        action="store_false",
        default=True,
        help="Skip station badges (line pills, facility tags); on by default",
    )
    render_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch the data file and regenerate on changes",
    )
    render_parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Watch interval in seconds",
    )

    bounds_parser = subparsers.add_parser(
        "bounds",
        help="Calculate station coordinate bounds",
    )
    bounds_parser.add_argument(
        "data",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to the metro map data JSON file",
    )

    pack_parser = subparsers.add_parser(
        "pack",
        help="Pack a map package directory into a zip archive",
    )
    pack_parser.add_argument(
        "source",
        type=Path,
        help="Path to the map package directory",
    )
    pack_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PACK_OUTPUT,
        help="Path to the output zip archive",
    )

    unpack_parser = subparsers.add_parser(
        "unpack",
        help="Unpack a zip archive into a map package directory",
    )
    unpack_parser.add_argument(
        "source",
        type=Path,
        help="Path to the map package zip archive",
    )
    unpack_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output directory",
    )

    return parser


def load_json_object(data_path: Path) -> dict[str, Any]:
    with data_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Map data must be a JSON object")
    return data


def merge_mapping_section(
    target: dict[str, Any],
    source: dict[str, Any],
    section_name: str,
) -> None:
    for key, value in source.items():
        if key in target:
            raise ValueError(f"Duplicate {section_name} id: {key}")
        target[key] = value


def merge_connections(
    target: list[dict[str, Any]],
    source: list[Any],
) -> None:
    for item in source:
        if not isinstance(item, dict):
            raise ValueError("Connection entries must be JSON objects")
        target.append(item)


def merge_map_fragment(
    merged: dict[str, Any],
    fragment: dict[str, Any],
    *,
    is_root: bool,
) -> None:
    if is_root:
        for key in ("id", "meta", "pricing"):
            value = fragment.get(key)
            if value is not None:
                merged[key] = value

    stations = fragment.get("stations")
    if stations is not None:
        if not isinstance(stations, dict):
            raise ValueError("stations must be a JSON object")
        merge_mapping_section(merged["stations"], stations, "station")

    lines = fragment.get("lines")
    if lines is not None:
        if not isinstance(lines, dict):
            raise ValueError("lines must be a JSON object")
        merge_mapping_section(merged["lines"], lines, "line")

    trains = fragment.get("trains")
    if trains is not None:
        if not isinstance(trains, dict):
            raise ValueError("trains must be a JSON object")
        merge_mapping_section(merged["trains"], trains, "train")

    connections = fragment.get("connections")
    if connections is not None:
        if not isinstance(connections, list):
            raise ValueError("connections must be a JSON array")
        merge_connections(merged["connections"], connections)


def build_merged_map(fragments: list[tuple[dict[str, Any], bool]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "stations": {},
        "lines": {},
        "trains": {},
        "connections": [],
    }
    for fragment, is_root in fragments:
        merge_map_fragment(merged, fragment, is_root=is_root)
    validate_train_references(merged)
    return merged


def validate_train_references(merged: dict[str, Any]) -> None:
    trains = merged.get("trains")
    lines = merged.get("lines")
    if not isinstance(trains, dict) or not isinstance(lines, dict):
        return

    for line in lines.values():
        if not isinstance(line, dict):
            continue

        train_info = line.get("trainInfo")
        if not isinstance(train_info, dict):
            continue

        invalid_keys = {str(key) for key in train_info} - {"rollingStockRefs"}
        if invalid_keys:
            invalid_list = ", ".join(sorted(invalid_keys))
            raise ValueError(
                f"trainInfo only supports rollingStockRefs; found: {invalid_list}"
            )

        rolling_stock_refs = train_info.get("rollingStockRefs")
        if rolling_stock_refs is None:
            continue
        if not isinstance(rolling_stock_refs, list):
            raise ValueError("trainInfo.rollingStockRefs must be a JSON array")

        for train_id in rolling_stock_refs:
            if not isinstance(train_id, str):
                raise ValueError("trainInfo.rollingStockRefs entries must be strings")
            train = trains.get(train_id)
            if not isinstance(train, dict):
                raise ValueError(f"Unknown train id: {train_id}")


def load_map_package_dir(package_dir: Path) -> dict[str, Any]:
    if not package_dir.is_dir():
        raise ValueError(f"Map package directory not found: {package_dir}")

    fragments: list[tuple[dict[str, Any], bool]] = []
    root_file = package_dir / "map.json"
    if root_file.exists():
        fragments.append((load_json_object(root_file), True))

    for section in ("stations", "lines", "trains", "connections"):
        section_dir = package_dir / section
        if not section_dir.exists():
            continue
        if not section_dir.is_dir():
            raise ValueError(f"Package section must be a directory: {section_dir}")
        for fragment_path in sorted(section_dir.glob("*.json")):
            fragments.append((load_json_object(fragment_path), False))

    if not fragments:
        raise ValueError("Map package is empty")

    return build_merged_map(fragments)


def load_map_package_zip(archive_path: Path) -> dict[str, Any]:
    if archive_path.suffix.lower() != ".zip":
        raise ValueError(f"Unsupported package archive format: {archive_path.suffix}")

    fragments: list[tuple[dict[str, Any], bool]] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if not name.endswith("/")
            and (
                name == "map.json"
                or name.startswith("stations/")
                or name.startswith("lines/")
                or name.startswith("trains/")
                or name.startswith("connections/")
            )
            and name.endswith(".json")
        )

        for name in names:
            with archive.open(name) as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError(f"Package fragment must be a JSON object: {name}")
            fragments.append((data, name == "map.json"))

    if not fragments:
        raise ValueError("Map package archive is empty")

    return build_merged_map(fragments)


def load_map_data(data_path: Path) -> dict[str, Any]:
    if data_path.is_dir():
        return load_map_package_dir(data_path)
    if data_path.suffix.lower() == ".zip":
        return load_map_package_zip(data_path)
    return build_merged_map([(load_json_object(data_path), True)])


def get_data_source_mtime(data_path: Path) -> float:
    if data_path.is_dir():
        mtimes = [
            path.stat().st_mtime for path in data_path.rglob("*") if path.is_file()
        ]
        if not mtimes:
            return data_path.stat().st_mtime
        return max(mtimes)
    return data_path.stat().st_mtime


def pack_map_package(source_dir: Path, output_path: Path) -> None:
    if not source_dir.is_dir():
        raise ValueError(f"Map package directory not found: {source_dir}")

    load_map_package_dir(source_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))


def unpack_map_package(source_path: Path, output_dir: Path) -> None:
    if source_path.suffix.lower() != ".zip":
        raise ValueError(f"Unsupported package archive format: {source_path.suffix}")

    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive entry: {member.filename}")
        archive.extractall(output_dir)

    load_map_package_dir(output_dir)


def resolve_font_paths(fonts: Sequence[str] | None) -> list[str]:
    if fonts is None:
        return list(DEFAULT_FONT_PATHS)
    return [font for font in fonts if font]


def scale_station_coordinates(
    data: dict[str, Any],
    scale: float,
) -> dict[str, Any]:
    if scale <= 0:
        raise ValueError("Scale must be greater than zero")
    if scale == 1.0:
        return data

    scaled_data = copy.deepcopy(data)
    stations = scaled_data.get("stations")
    if not isinstance(stations, dict):
        return scaled_data

    for station in stations.values():
        if not isinstance(station, dict):
            continue

        x = station.get("x")
        y = station.get("y")
        if isinstance(x, int | float):
            station["x"] = round(float(x) * scale, 2)
        if isinstance(y, int | float):
            station["y"] = round(float(y) * scale, 2)

    return scaled_data


def calculate_bounds(data: dict[str, Any]) -> tuple[float, float, float, float]:
    stations = data.get("stations")
    if not isinstance(stations, dict) or not stations:
        raise ValueError("Map data must contain at least one station")

    x_values: list[float] = []
    y_values: list[float] = []
    for station in stations.values():
        if not isinstance(station, dict):
            continue

        x = station.get("x")
        y = station.get("y")
        if isinstance(x, int | float) and isinstance(y, int | float):
            x_values.append(float(x))
            y_values.append(float(y))

    if not x_values or not y_values:
        raise ValueError("No valid station coordinates found")

    return min(x_values), max(x_values), min(y_values), max(y_values)


def convert_svg_to_png(svg_path: Path, png_path: Path) -> None:
    converter = shutil.which("rsvg-convert")
    if converter is None:
        raise RuntimeError("rsvg-convert is required for svg-png render mode")

    png_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [converter, str(svg_path), "-o", str(png_path)],
        check=True,
    )


def format_bounds(bounds: tuple[float, float, float, float]) -> str:
    min_x, max_x, min_y, max_y = bounds
    return "\n".join(
        [
            f"min_x: {min_x}",
            f"max_x: {max_x}",
            f"min_y: {min_y}",
            f"max_y: {max_y}",
        ]
    )


def render_map(
    data_path: Path,
    output_path: Path,
    background_path: Path | None = None,
    font_paths: Sequence[str] | None = None,
    scale: float = 1.0,
    mode: str = "pil",
    renderer: Renderer = draw_metro_map,
    svg_png_converter: SvgPngConverter = convert_svg_to_png,
) -> bool:
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        return False

    try:
        data = load_map_data(data_path)
        scaled_data = scale_station_coordinates(data, scale)
        actual_output_path = output_path
        temporary_svg_path: Path | None = None
        if mode == "svg":
            actual_output_path = output_path.with_suffix(".svg")
        elif mode == "svg-png":
            temporary_svg_path = output_path.with_suffix(output_path.suffix + ".svg")
            actual_output_path = temporary_svg_path
        elif mode != "pil":
            raise ValueError(f"Unsupported render mode: {mode}")

        renderer(
            scaled_data,
            str(actual_output_path),
            None if background_path is None else str(background_path),
            resolve_font_paths(font_paths),
        )
        if temporary_svg_path is not None:
            svg_png_converter(temporary_svg_path, output_path)
            temporary_svg_path.unlink(missing_ok=True)
    except Exception as exc:
        print(f"Error: {exc}")
        return False

    print(f"Rendered preview: {output_path}")
    return True


def watch_render(
    data_path: Path,
    output_path: Path,
    background_path: Path | None = None,
    font_paths: Sequence[str] | None = None,
    scale: float = 1.0,
    mode: str = "pil",
    interval: float = 1.0,
    renderer: Renderer = draw_metro_map,
    render_func: RenderFunc = render_map,
    sleep_func: SleepFunc = time.sleep,
    max_iterations: int | None = None,
) -> None:
    last_mtime: float | None = None
    iterations = 0

    while max_iterations is None or iterations < max_iterations:
        try:
            if data_path.exists():
                mtime = get_data_source_mtime(data_path)
                if mtime != last_mtime:
                    render_func(
                        data_path,
                        output_path,
                        background_path,
                        font_paths,
                        scale,
                        mode,
                        renderer,
                    )
                    last_mtime = mtime
        except Exception as exc:
            print(f"Error: {exc}")

        iterations += 1
        sleep_func(interval)


def build_cli_renderer(*, badges: bool, preview: bool) -> Renderer:
    def renderer(
        data: dict[str, Any],
        output_path: str,
        bg_path: str | None,
        font_paths: list[str] | None,
    ) -> None:
        draw_metro_map(
            data,
            output_path,
            bg_path,
            font_paths,
            badges_enabled=badges,
            preview_max_edge=1600 if preview else None,
        )

    return renderer


def run_render_command(args: argparse.Namespace) -> int:
    font_paths = resolve_font_paths(args.fonts)
    renderer = build_cli_renderer(
        badges=bool(getattr(args, "badges", True)),
        preview=bool(getattr(args, "preview", False)),
    )
    if args.watch:
        watch_render(
            data_path=args.data,
            output_path=args.output,
            background_path=args.background,
            font_paths=font_paths,
            scale=args.scale,
            mode=args.mode,
            interval=args.interval,
            renderer=renderer,
        )
        return 0

    return (
        0
        if render_map(
            data_path=args.data,
            output_path=args.output,
            background_path=args.background,
            font_paths=font_paths,
            scale=args.scale,
            mode=args.mode,
            renderer=renderer,
        )
        else 1
    )


def run_bounds_command(args: argparse.Namespace) -> int:
    try:
        data = load_map_data(args.data)
        print(format_bounds(calculate_bounds(data)))
    except FileNotFoundError:
        print(f"Data file not found: {args.data}")
        return 1
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    return 0


def run_pack_command(args: argparse.Namespace) -> int:
    try:
        pack_map_package(args.source, args.output)
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Packed map package: {args.output}")
    return 0


def run_unpack_command(args: argparse.Namespace) -> int:
    try:
        unpack_map_package(args.source, args.output)
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Unpacked map package: {args.output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "render":
        return run_render_command(args)
    if args.command == "bounds":
        return run_bounds_command(args)
    if args.command == "pack":
        return run_pack_command(args)
    if args.command == "unpack":
        return run_unpack_command(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

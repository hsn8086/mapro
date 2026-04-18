from __future__ import annotations

from collections import defaultdict


def _resolve_station_status(station_item: dict | str) -> str:
    if not isinstance(station_item, dict):
        return "active"

    status = station_item.get("status")
    if not status:
        return "active"

    return str(status)


def build_station_markers(lines: dict) -> dict[str, list[dict]]:
    station_markers: dict[str, list[dict]] = defaultdict(list)
    for line_id, line in lines.items():
        line_color = line.get("color", "#000000")
        line_stations = line.get("stations", [])
        for s_item in line_stations:
            if isinstance(s_item, dict):
                sid = s_item.get("id")
                props = s_item
            else:
                sid = s_item
                props = {}

            if not sid:
                continue

            markers: list[str] = []
            num = props.get("num")
            if num:
                markers.append(num)

            service = props.get("service")
            if service and service in ["rapid", "express"]:
                label = "快" if service == "rapid" else "特"
                markers.append(label)

            if markers:
                station_markers[sid].append(
                    {
                        "line_id": line_id,
                        "color": line_color,
                        "texts": markers,
                        "active": _resolve_station_status(s_item) == "active",
                    }
                )

    return station_markers

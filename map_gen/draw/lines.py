from __future__ import annotations


def draw_lines(
    draw,
    line_polylines: dict[str, list[tuple[int, int]]],
    line_meta: dict[str, dict],
    lines: dict,
    segment_map: dict[tuple[tuple[int, int], tuple[int, int]], list[str]],
    segment_offsets: dict[tuple[tuple[int, int], tuple[int, int]], dict[str, int]],
    styles: dict[str, float | str],
    line_width: float,
) -> None:
    color_inactive = styles["COLOR_INACTIVE"]

    draw_buffer_inactive: list[
        tuple[tuple[float, float], tuple[float, float], str, float]
    ] = []
    draw_buffer_active: list[
        tuple[tuple[float, float], tuple[float, float], str, float]
    ] = []

    for line_id, polyline in line_polylines.items():
        line_data = lines[line_id]
        base_color = line_data.get("color", "#000000")
        line_status = line_data.get("status", "active")

        if line_status != "active":
            base_color = color_inactive

        line_draw_state_station_idx = 0

        for i in range(len(polyline) - 1):
            p1 = polyline[i]
            p2 = polyline[i + 1]

            l_meta = line_meta.get(line_id)
            if not l_meta:
                continue

            if "point_map" not in l_meta:
                l_meta["point_map"] = {
                    pt: idx for idx, pt in enumerate(l_meta["points"])
                }

            pt_map = l_meta["point_map"]

            if p1 in pt_map:
                line_draw_state_station_idx = pt_map[p1]

            s_idx = line_draw_state_station_idx
            statuses = l_meta["statuses"]

            is_planned_segment = False
            if s_idx < len(statuses) and statuses[s_idx] == "planned":
                is_planned_segment = True
            if s_idx + 1 < len(statuses) and statuses[s_idx + 1] == "planned":
                is_planned_segment = True

            color = color_inactive if is_planned_segment else base_color

            key = (p2, p1) if p1 > p2 else (p1, p2)
            group = segment_map[key]
            total_lines = len(group)

            if line_id not in segment_offsets[key]:
                my_index = 0
            else:
                my_index = segment_offsets[key][line_id]

            c_p1, c_p2 = key
            c_dx = c_p2[0] - c_p1[0]
            c_dy = c_p2[1] - c_p1[1]
            c_len = (c_dx * c_dx + c_dy * c_dy) ** 0.5
            if c_len == 0:
                continue

            c_ux = -c_dy / c_len
            c_uy = c_dx / c_len

            line_type = lines[line_id].get("type", "subway")
            is_tram = line_type == "tram"

            slot_width = line_width / total_lines

            draw_thickness = slot_width
            if is_tram and total_lines == 1:
                draw_thickness = slot_width * 0.5

            draw_thickness = max(1.5, draw_thickness)

            if abs(draw_thickness - slot_width) < 0.1:
                draw_thickness = int(draw_thickness + 1.5)

            offset_from_center = -line_width / 2.0 + slot_width * (my_index + 0.5)

            ox = c_ux * offset_from_center
            oy = c_uy * offset_from_center

            real_p1 = (p1[0] + ox, p1[1] + oy)
            real_p2 = (p2[0] + ox, p2[1] + oy)

            item = (real_p1, real_p2, str(color), draw_thickness)
            if color == color_inactive:
                draw_buffer_inactive.append(item)
            else:
                draw_buffer_active.append(item)

    def execute_draw_buffer(
        buffer: list[tuple[tuple[float, float], tuple[float, float], str, float]],
    ) -> None:
        for p1, p2, col, thick in buffer:
            w = int(thick)
            draw.line([p1, p2], fill=col, width=w)

            r_cap = (thick - 1) / 2.0
            if r_cap < 0:
                r_cap = 0

            if thick > 2:
                draw.ellipse(
                    [p1[0] - r_cap, p1[1] - r_cap, p1[0] + r_cap, p1[1] + r_cap],
                    fill=col,
                )
                draw.ellipse(
                    [p2[0] - r_cap, p2[1] - r_cap, p2[0] + r_cap, p2[1] + r_cap],
                    fill=col,
                )

    execute_draw_buffer(draw_buffer_inactive)
    execute_draw_buffer(draw_buffer_active)

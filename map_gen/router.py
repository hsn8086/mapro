from .geometry import get_dir, get_turn_cost, sign


def get_path_score(points, prev_dir=None, target_dir=None):
    """对路径点列进行评分"""
    if len(points) < 2:
        return 0

    score = 0
    segments = []

    for i in range(len(points) - 1):
        d = get_dir(points[i], points[i + 1])
        segments.append(d)

    # 1. 基础段数惩罚
    score += max(0, len(segments) - 1) * 40

    curr_dir = prev_dir

    for i, d in enumerate(segments):
        # 转角惩罚
        score += get_turn_cost(curr_dir, d)

        # 掉头/反向惩罚
        if target_dir:
            if target_dir[0] != 0 and d[0] == -target_dir[0]:
                score += 500
            if target_dir[1] != 0 and d[1] == -target_dir[1]:
                score += 500

        # 初始方向对齐判定
        if i == 0 and curr_dir and curr_dir != (0, 0):
            if d != curr_dir:
                if d == target_dir:
                    pass
                else:
                    score += 200

        curr_dir = d

    return score


def generate_octile_candidates(p1, p2, allow_split=True):
    """生成 p1 到 p2 的所有合法八向路径候选"""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1

    candidates = []

    if dx == 0 or dy == 0 or abs(dx) == abs(dy):
        return [[p1, p2]]

    sx, sy = sign(dx), sign(dy)
    min_d = min(abs(dx), abs(dy))

    rem_x = dx - sx * min_d
    rem_y = dy - sy * min_d

    # A: Straight -> Diag
    m1 = (x1 + rem_x, y1 + rem_y)
    candidates.append([p1, m1, p2])

    # B: Diag -> Straight
    m2 = (x1 + sx * min_d, y1 + sy * min_d)
    candidates.append([p1, m2, p2])

    # C: Half Straight -> Diag -> Half Straight
    if allow_split and (abs(rem_x) > 1 or abs(rem_y) > 1):
        hx, hy = int(rem_x / 2), int(rem_y / 2)
        split_p1 = (x1 + hx, y1 + hy)
        split_p2 = (split_p1[0] + sx * min_d, split_p1[1] + sy * min_d)
        candidates.append([p1, split_p1, split_p2, p2])

    return candidates


def octile_path(p1, p2, prev_dir=None):
    if p1 == p2:
        return [p1]

    candidates = generate_octile_candidates(p1, p2, allow_split=True)
    target_dir = (sign(p2[0] - p1[0]), sign(p2[1] - p1[1]))
    candidates.sort(key=lambda path: get_path_score(path, prev_dir, target_dir))
    return candidates[0]


def build_line_polyline(points):
    if len(points) <= 1:
        return points

    full_path = [points[0]]
    prev_dir = None

    for i in range(1, len(points)):
        p_start = points[i - 1]
        p_end = points[i]
        seg = octile_path(p_start, p_end, prev_dir)

        if len(seg) >= 2:
            prev_dir = get_dir(seg[-2], seg[-1])

        full_path.extend(seg[1:])

    return full_path

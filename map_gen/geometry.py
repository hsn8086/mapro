def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def get_dir(p1, p2):
    """计算 p1 -> p2 的单位方向向量"""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    if dx == 0 and dy == 0:
        return (0, 0)
    return (sign(dx), sign(dy))


def get_turn_cost(d1, d2):
    """计算转角代价：越小越好"""
    if d1 == (0, 0) or d2 == (0, 0) or d1 is None or d2 is None:
        return 0
    if d1 == d2:
        return 0

    # 点积判断角度
    dot = d1[0] * d2[0] + d1[1] * d2[1]

    if dot == 1:
        return 1  # 45°
    if dot == 0:
        return 60  # 90°
    if dot == -1:
        return 20  # 135°
    return 100  # 180°

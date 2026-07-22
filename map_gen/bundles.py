from __future__ import annotations

from dataclasses import dataclass

from .geometry import get_dir

Point = tuple[int, int]
SegmentKey = tuple[Point, Point]


@dataclass(frozen=True)
class BundleChain:
    """A maximal run of consecutive shared segments (a corridor).

    Chains detected per shared-line-set are merged into corridors whenever
    they connect end to end and keep at least two lines in common, so a
    line travelling the whole corridor keeps a single slot even if other
    members join or leave along the way.
    """

    keys: tuple[SegmentKey, ...]
    line_ids: tuple[str, ...]
    # ordered vertices in the orientation of the first line that walked it
    vertices: tuple[Point, ...]


def _canonical_key(p1: Point, p2: Point) -> SegmentKey:
    return (p2, p1) if p1 > p2 else (p1, p2)


def _find_run_bounds(
    polyline: list[Point], keys: set[SegmentKey]
) -> tuple[int, int] | None:
    """Locate the (first) consecutive run of `keys` inside a polyline."""
    start: int | None = None
    for index in range(len(polyline) - 1):
        key = _canonical_key(polyline[index], polyline[index + 1])
        if key in keys:
            if start is None:
                start = index
        elif start is not None:
            return (start, index)
    if start is not None:
        return (start, len(polyline) - 1)
    return None


def _detect_chains(
    line_polylines: dict[str, list[Point]],
    segment_map: dict[SegmentKey, list[str]],
) -> list[BundleChain]:
    chains: list[BundleChain] = []
    seen: set[tuple[tuple[str, ...], frozenset[SegmentKey]]] = set()

    for line_id, polyline in line_polylines.items():
        run_group: tuple[str, ...] | None = None
        run_start = 0
        for index in range(len(polyline)):
            group: tuple[str, ...] | None = None
            if index < len(polyline) - 1:
                key = _canonical_key(polyline[index], polyline[index + 1])
                group = tuple(sorted(set(segment_map.get(key, [line_id]))))
            if group == run_group:
                continue
            if run_group is not None and len(run_group) > 1:
                keys = tuple(
                    _canonical_key(polyline[i], polyline[i + 1])
                    for i in range(run_start, index)
                )
                marker = (run_group, frozenset(keys))
                if marker not in seen:
                    seen.add(marker)
                    chains.append(
                        BundleChain(
                            keys=keys,
                            line_ids=run_group,
                            vertices=tuple(polyline[run_start : index + 1]),
                        )
                    )
            run_group = group
            run_start = index

    return chains


def _try_join(a: BundleChain, b: BundleChain) -> BundleChain | None:
    if len(set(a.line_ids) & set(b.line_ids)) < 2:
        return None
    av, bv = a.vertices, b.vertices
    if av[-1] == bv[0]:
        vertices = av + bv[1:]
    elif av[-1] == bv[-1]:
        vertices = av + tuple(reversed(bv[:-1]))
    elif av[0] == bv[-1]:
        vertices = bv + av[1:]
    elif av[0] == bv[0]:
        vertices = tuple(reversed(bv)) + av[1:]
    else:
        return None
    keys = tuple(
        _canonical_key(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)
    )
    return BundleChain(
        keys=keys,
        line_ids=tuple(sorted(set(a.line_ids) | set(b.line_ids))),
        vertices=vertices,
    )


def _merge_corridors(chains: list[BundleChain]) -> list[BundleChain]:
    pool = list(chains)
    merged = True
    while merged:
        merged = False
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                joined = _try_join(pool[i], pool[j])
                if joined is not None:
                    pool[i] = joined
                    del pool[j]
                    merged = True
                    break
            if merged:
                break
    return pool


def _direction_sign(chain_dir: tuple[int, int], approach_dir: tuple[int, int]) -> int:
    cross = chain_dir[0] * approach_dir[1] - chain_dir[1] * approach_dir[0]
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


@dataclass(frozen=True)
class _MemberGeometry:
    continues_entry: bool
    continues_exit: bool
    side: int
    join_pos: int
    coverage: int
    covered_keys: frozenset[SegmentKey]


def _member_geometry(
    chain: BundleChain, polyline: list[Point]
) -> _MemberGeometry | None:
    """Geometry of one member line relative to the corridor orientation."""
    keys = set(chain.keys)
    bounds = _find_run_bounds(polyline, keys)
    if bounds is None:
        return None
    run_start, run_end = bounds

    first_key = _canonical_key(polyline[run_start], polyline[run_start + 1])
    key_index = chain.keys.index(first_key)
    corridor_travel = get_dir(chain.vertices[key_index], chain.vertices[key_index + 1])
    line_travel = get_dir(polyline[run_start], polyline[run_start + 1])
    forward = corridor_travel == line_travel

    entry_vertex = polyline[run_start]
    exit_vertex = polyline[run_end]

    entry_dir_in = (
        get_dir(polyline[run_start - 1], entry_vertex) if run_start > 0 else None
    )
    entry_dir_out = get_dir(polyline[run_start], polyline[run_start + 1])
    exit_dir_in = get_dir(polyline[run_end - 1], polyline[run_end])
    exit_dir_out = (
        get_dir(exit_vertex, polyline[run_end + 1])
        if run_end + 1 < len(polyline)
        else None
    )

    # a terminus is not a continuation: the through line must actually keep
    # travelling past the chain boundary without turning
    continues_entry = entry_dir_in is not None and entry_dir_in == entry_dir_out
    continues_exit = exit_dir_out is not None and exit_dir_out == exit_dir_in

    # approach side: look at whichever end has an actual turn into the chain.
    # entry: the joiner's origin sits on the side opposite its travel vector;
    # exit: the destination side is simply where the departure vector points.
    side = 0
    if entry_dir_in is not None and entry_dir_in != entry_dir_out:
        side = _direction_sign(entry_dir_out, (-entry_dir_in[0], -entry_dir_in[1]))
    elif exit_dir_out is not None and exit_dir_out != exit_dir_in:
        side = _direction_sign(exit_dir_in, exit_dir_out)

    if not forward:
        # express in chain orientation
        continues_entry, continues_exit = continues_exit, continues_entry
        side = -side

    join_pos = 0
    try:
        join_pos = chain.vertices.index(entry_vertex if forward else exit_vertex)
    except ValueError:
        join_pos = 0

    covered = frozenset(
        _canonical_key(polyline[i], polyline[i + 1]) for i in range(run_start, run_end)
    )
    return _MemberGeometry(
        continues_entry=continues_entry,
        continues_exit=continues_exit,
        side=side,
        join_pos=join_pos,
        coverage=run_end - run_start,
        covered_keys=covered,
    )


def _natural_line_order(line_id: str) -> tuple[int, str]:
    digits = ""
    for ch in line_id:
        if ch.isdigit():
            digits += ch
        else:
            break
    return (int(digits) if digits else 1_000_000, line_id)


def build_bundle_offsets(
    line_polylines: dict[str, list[Point]],
    segment_map: dict[SegmentKey, list[str]],
    *,
    slot_spacing: float,
) -> dict[tuple[str, SegmentKey], float]:
    """Anchored slot offsets for every (line, shared segment).

    Within each corridor the anchor line (widest coverage, then the one
    that continues at both of its ends) keeps its original alignment
    (offset 0); joining lines stack on their approach side, later joiners
    farther out, and keep the same slot for their entire stay. Offsets are
    lateral distances measured along the canonical-direction left normal
    of each segment.
    """
    offsets: dict[tuple[str, SegmentKey], float] = {}

    for chain in _merge_corridors(_detect_chains(line_polylines, segment_map)):
        members: dict[str, _MemberGeometry] = {}
        for line_id in chain.line_ids:
            geometry = _member_geometry(chain, line_polylines.get(line_id, []))
            if geometry is not None:
                members[line_id] = geometry
        if not members:
            continue

        def anchor_rank(line_id: str) -> tuple[int, int, tuple[int, str]]:
            geometry = members[line_id]
            return (
                -geometry.coverage,
                -(int(geometry.continues_entry) + int(geometry.continues_exit)),
                _natural_line_order(line_id),
            )

        anchor = min(members, key=anchor_rank)
        slot_values: dict[str, float] = {anchor: 0.0}

        stacked: dict[int, int] = {1: 0, -1: 0}
        rest = sorted(
            (lid for lid in members if lid != anchor),
            key=lambda lid: (members[lid].join_pos, lid),
        )
        for line_id in rest:
            side = members[line_id].side
            if side == 0:
                side = 1 if stacked[1] <= stacked[-1] else -1
            stacked[side] += 1
            slot_values[line_id] = side * stacked[side] * slot_spacing

        # convert chain-oriented lateral values into canonical-normal scalars,
        # emitting only the keys each line actually traverses
        for index, key in enumerate(chain.keys):
            v1 = chain.vertices[index]
            v2 = chain.vertices[index + 1]
            travel = get_dir(v1, v2)
            canonical = get_dir(*key)
            flip = 1.0 if travel == canonical else -1.0
            for line_id, value in slot_values.items():
                if key in members[line_id].covered_keys:
                    offsets[(line_id, key)] = value * flip

    return offsets

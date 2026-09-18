from __future__ import annotations

ROSA_CHAIR = {
    2: [1,2,3,4,5,6,7,8], 3: [2,2,3,4,5,6,7,8],
    4: [3,3,3,4,5,6,7,8], 5: [4,4,4,4,5,6,7,8],
    6: [5,5,5,5,6,7,8,9], 7: [6,6,6,7,7,8,8,9],
    8: [7,7,7,8,8,9,9,9],
}
ROSA_SECTION_B = {
    0: [1,1,1,2,3,4,5,6], 1: [1,1,2,2,3,4,5,6],
    2: [1,2,2,3,3,4,6,7], 3: [2,2,3,3,4,5,6,8],
    4: [3,3,4,4,5,6,7,8], 5: [4,4,5,5,6,7,8,9],
    6: [5,5,6,7,8,8,9,9],
}
ROSA_SECTION_C = {
    0: [1,1,1,2,3,4,5,6], 1: [1,1,2,3,4,5,6,7],
    2: [1,2,2,3,4,5,6,7], 3: [2,3,3,3,5,6,7,8],
    4: [3,4,4,5,5,6,7,8], 5: [4,5,5,6,6,7,8,9],
    6: [5,6,6,7,7,8,8,9], 7: [6,7,7,8,8,9,9,9],
}
ROSA_MON_PERI = {
    1:[1,2,3,4,5,6,7,8,9], 2:[2,2,3,4,5,6,7,8,9],
    3:[3,3,3,4,5,6,7,8,9], 4:[4,4,4,4,5,6,7,8,9],
    5:[5,5,5,5,5,6,7,8,9], 6:[6,6,6,6,6,6,7,8,9],
    7:[7,7,7,7,7,7,7,8,9], 8:[8,8,8,8,8,8,8,8,9],
    9:[9,9,9,9,9,9,9,9,9],
}
ROSA_FINAL = {i: [max(i, j) for j in range(1, 11)] for i in range(1, 11)}


def _lookup(table: dict[int, list[int]], row: int, col: int, col_offset: int) -> int:
    rows = sorted(table)
    row = max(rows[0], min(rows[-1], int(row)))
    idx = max(0, min(len(table[row]) - 1, int(col) - col_offset))
    return int(table[row][idx])


def compute_rosa(
    a1: int, a2: int, a3: int, a4: int, duration_chair: int,
    b1: int, b2: int, duration_monitor: int, duration_phone: int,
    c1: int, c2: int, duration_mouse: int, duration_keyboard: int,
) -> dict[str, int | str]:
    chair_raw = _lookup(ROSA_CHAIR, a1 + a2, a3 + a4, 2)
    chair = max(1, min(10, chair_raw + duration_chair))

    b1s = max(0, b1 + duration_monitor)
    b2s = max(0, b2 + duration_phone)
    sec_b = _lookup(ROSA_SECTION_B, b2s, b1s, 0)

    c1s = max(0, c1 + duration_mouse)
    c2s = max(0, c2 + duration_keyboard)
    sec_c = _lookup(ROSA_SECTION_C, c2s, c1s, 0)

    mon_peri = _lookup(ROSA_MON_PERI, sec_b, sec_c, 1)
    final = _lookup(ROSA_FINAL, chair, mon_peri, 1)

    # The original validation supports 5 as the action level.
    action = "action_level_reached" if final >= 5 else "below_action_level"
    return {
        "chair": chair,
        "section_b": sec_b,
        "section_c": sec_c,
        "monitor_peripherals": mon_peri,
        "final": final,
        "action": action,
    }

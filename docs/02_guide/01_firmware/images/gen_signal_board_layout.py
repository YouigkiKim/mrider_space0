#!/usr/bin/env python3
"""Team (Korean) version of the signal perfboard layout - the board the Teensy plugs into.

Usage (from the repository root):
    python3 docs/02_guide/01_firmware/images/gen_signal_board_layout.py            # write the SVG
    python3 docs/02_guide/01_firmware/images/gen_signal_board_layout.py --table    # print the wire table (markdown)

Writes signal_board_layout.svg next to this file.

WHERE THE LAYOUT COMES FROM
---------------------------
Every hole position and every connection is READ from the professor's generator,
scripts/gen_signal_board_figure.py (source of docs/images/signal-board-perfboard-layout.svg,
docs/build/03-electrical.md §3.5.4). Nothing is re-typed, so if the original layout changes,
re-running this script follows it. Importing that module does not rewrite its SVG.

WHAT THE TEAM CHANGES
---------------------
1. R5 is a WIRE LINK and R6 is omitted: the FS-iA6B i-BUS signal idles at 3.3 V, measured on
   2026-11-14 (docs/03_validation/01_firmware/02_steering_bench.md §1) - the 3.3 V row of the
   R5/R6 table in 03-electrical.md §3.5.4. The R6 holes stay free (empty outline).
2. EVERY insulated wire is routed on the BACK (solder side), along the hole grid, with right-angle
   bends instead of the original's straight diagonals. Reason: every wire ends on a socket,
   terminal or header pin, and on the front those pads sit under the part's plastic body - an
   iron cannot reach them. The connections (which hole joins which) are exactly the original's.
3. Terminal blocks lie ACROSS: both pins in one row (holes c and c+2), so the plug's wire leaves
   toward the board edge it is going to. The original's upper pin becomes the left pin. The body
   size and pin row are ASSUMED (TERM_LEN, TERM_DEPTH, TERM_ROW) until the header is measured.
4. A wire the original lands on a bus may land on the nearest free hole of the SAME bus net - it is
   the same copper. The two 3.3 V buses are separate nets (joined only inside the Teensy).
5. Labels and panels in Korean.

ROUTING RULES (asserted)
------------------------
- A wire runs only horizontally or vertically through hole centres, and is soldered only at its
  two ends. It never passes over a hole that holds anything (pin, lead, stub, terminal, another
  wire's end), nor over the R3/R4 bodies (which lie on the back).
- It may cross a bare bus at right angles (the bus is on the front), and cross another wire at
  right angles - never bend there, never run along it.
- Routes are found by a shortest-path search (cost: length + bends + crossings), trying many
  wire orders and keeping the best, with a fixed seed so the drawing is reproducible.

The original's assertions (no hole carries three, reverse side exactly where a bus is crossed,
every bus fed, every used pin reached) are re-run on the changed layout.
"""
import heapq
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_signal_board_figure as G  # noqa: E402  (layout data + check(); does not write on import)

# ------------------------------------------------------------ team change 1: R5 link
I_BUS = "#be123c"
G.PARTS = [p for p in G.PARTS if p[0] not in ("R5", "R6")]
R5_LINK = ((23, 4), (23, 8))                  # the two holes the original gives R5
R6_FREE = ((23, 10), (27, 10))                # the holes the original gives R6, left empty
ORIG = [(a, b, col) for a, b, col, _ in G.JUMPERS]     # the original's wires

hx, hy, P = G.hx, G.hy, G.P
COLS, ROWS, BORDER = G.COLS, G.ROWS, G.BORDER
LO, HI = 1 + BORDER, COLS - BORDER            # usable ring

# What each wire is for, keyed by the original's two holes (its comments, in Korean).
ROLE_BY_HOLES = {
    ((5, 11), (5, 6)): "3V3 패드 → 3.3 V(위) 버스",
    ((17, 17), (17, 24)): "3V3 패드 → 3.3 V(아래) 버스",
    ((3, 17), (3, 21)): "GND 패드 → GND 버스",
    ((3, 2), (3, 11)): "PWR +5 V → Vin",
    ((3, 4), (4, 11)): "PWR GND → GND 패드",
    ((8, 2), (8, 11)): "RELAY GATE → 핀 21",
    ((8, 4), (9, 11)): "RELAY SENSE → 핀 20",
    ((14, 2), (11, 10)): "STRS SDA → 핀 18 스텁",
    ((14, 4), (10, 10)): "STRS SCL → 핀 19 스텁",
    ((19, 2), (19, 6)): "STRP 3.3 V → 3.3 V(위) 버스",
    ((19, 4), (17, 11)): "STRP GND → GND 패드",
    ((7, 26), (4, 20)): "DRVS A → 핀 0 스텁",
    ((7, 28), (5, 20)): "DRVS B → 핀 1 스텁",
    ((12, 26), (12, 24)): "DRVP 3.3 V → 3.3 V(아래) 버스",
    ((12, 28), (12, 21)): "DRVP GND → GND 버스",
    ((23, 2), (23, 4)): "i-BUS 신호 → R5",
    ((23, 9), (14, 11)): "R5 → 핀 15",
    ((25, 2), (27, 2)): "i-BUS GND → GND 세로선",
    ((17, 28), (6, 17)): "PWM 1 신호 → 핀 2",
    ((19, 28), (19, 21)): "PWM 1 GND → GND 버스",
    ((22, 28), (7, 17)): "PWM 2 신호 → 핀 3",
    ((24, 28), (24, 21)): "PWM 2 GND → GND 버스",
}
for a, b, _ in ORIG:
    assert (a, b) in ROLE_BY_HOLES, f"the original has a wire {a}->{b} this figure does not name"
ROLES = [ROLE_BY_HOLES[(a, b)] for a, b, _ in ORIG]

# ------------------------------------------------------------ team change 3: terminal blocks lie across
# EM Tech 2EDGK (PCB header) + 2EDGRC (plug), 5.08 mm: the two pins are two holes apart. The original
# stands them in one COLUMN, so the wire would leave sideways. The team lays them in one ROW, so the
# wire leaves toward the board edge it is going to. The 'up' pin of the original becomes the LEFT pin.
#
# ASSUMED until the part is measured - change these numbers and re-run, nothing else moves:
TERM_LEN = 4           # body length along the pins, holes (2 x 5.08 = 10.16 mm)
TERM_DEPTH = 3         # body depth across the pins, holes
TERM_ROW = {"top": 3, "bottom": 27}   # pin row: the middle row of the body
TERM_COL = {"PWR": 3, "RELAY": 8, "STRS": 13, "STRP": 18, "DRVS": 7, "DRVP": 12}   # left pin

REMAP, TERMS = {}, []
for d, c, r, up, lo, col in G.TERMINALS:
    side = "top" if r < ROWS // 2 else "bottom"
    nc, nr = TERM_COL[d], TERM_ROW[side]
    REMAP[(c, r)], REMAP[(c, r + 2)] = (nc, nr), (nc + 2, nr)
    TERMS.append((d, nc, nr, up, lo, col, side))
G.TERMINALS = [t[:6] for t in TERMS]
G.term_holes = lambda c, r: [(c, r), (c + 2, r)]      # the original's check() looks this up
WIRES0 = [(REMAP.get(a, a), REMAP.get(b, b), col) for a, b, col in ORIG]


def term_body(c, r):
    """Holes under a terminal body (pins at c and c+2 on row r)."""
    half = (TERM_LEN - 2) // 2
    return {(c + i, r + j) for i in range(-half, 2 + half + 1)
            for j in range(-(TERM_DEPTH // 2), TERM_DEPTH // 2 + 1)}


# no two bodies overlap, nothing of the front copper or a part sits under one
for i, (d, c, r, *_rest) in enumerate(TERMS):
    for d2, c2, r2, *_ in TERMS[i + 1:]:
        assert not (term_body(c, r) & term_body(c2, r2)), f"terminal {d} overlaps {d2}"
    for d2, c2, r2, *_ in G.HEADERS:
        assert not (term_body(c, r) & set(G.header_holes(c2, r2))), f"terminal {d} overlaps header {d2}"
    for _, row, (c0, c1), *_ in G.BUSES:
        assert not (term_body(c, r) & set(G.run(c0, row, c1, row))), f"terminal {d} sits on a bus"
    for pd, _, pa, pb, *_ in G.PARTS:
        assert pa not in term_body(c, r) and pb not in term_body(c, r), f"terminal {d} sits on {pd}"
    assert all(LO <= h[0] <= HI and LO <= h[1] <= HI for h in G.term_holes(c, r))


# ------------------------------------------------------------ team change 2: routing
def run(c0, r0, c1, r1):
    return G.run(c0, r0, c1, r1)


# Nets of bare copper. A wire that the original lands on a bus may land on ANY free hole of the same
# net - it is the same copper - so the router picks the nearest one. The two 3.3 V buses are separate
# nets (they meet only inside the Teensy); the GND spine and the GND bus are one.
NET = {}
for name, row, (c0, c1), *_ in G.BUSES:
    for h in run(c0, row, c1, row):
        NET[h] = "V33T" if name == "V33T" else ("V33B" if name == "V33B" else "GND")
for c, r0, r1, *_ in G.SPINES:
    for h in run(c, r0, c, r1):
        NET[h] = "GND"

BLOCK = set()                                  # holes a wire may not pass over
# The whole Teensy footprint, socket rows AND the rows between them: a pin is reached from the
# outside only. Letting a wire dive under the Teensy to reach a pin from the inside produced
# 40-hole detours (the RELAY/STRS corner), which is not a wire anybody would solder.
for c in range(G.T_COL0, G.T_COL0 + len(G.TOP_PINS)):
    for r in range(G.T_TOP, G.T_BOT + 1):
        BLOCK.add((c, r))
for _, _, a, b, *_ in G.PARTS:
    BLOCK.update((a, b))
for d, _, a, b, _, _, rev in G.PARTS:          # a part on the BACK lies along its whole run
    if rev:
        BLOCK.update(run(a[0], a[1], b[0], b[1]))
BLOCK.update(R5_LINK)
BLOCK.update(R6_FREE)
for d, c, r, *_ in G.TERMINALS:
    BLOCK.update(G.term_holes(c, r))
for d, c, r, *_ in G.HEADERS:
    BLOCK.update(G.header_holes(c, r))
for c, r0, r1, *_ in G.STUBS:
    BLOCK.update(run(c, r0, c, r1))
for a, b, _ in WIRES0:
    BLOCK.add(a)
    if b not in NET:
        BLOCK.add(b)


def targets(b):
    """Where wire end b may land: itself, or any free hole of its bus net."""
    if b not in NET:
        return {b}
    return {h for h, n in NET.items() if n == NET[b] and h not in BLOCK}


BODY = set()                                   # holes under a front body: passable, but avoided
for d, c, r, *_ in G.TERMINALS:
    BODY |= term_body(c, r)
for d, c, r, *_ in G.HEADERS:
    BODY.update(G.header_holes(c, r))

# The hole straight outside a socket pin that a wire ends on is that pin's only way in (its
# neighbours in the row are pins, the row behind it is under the Teensy). Another wire may cross
# it at a right angle but never bend there, or the pin is walled off.
APPROACH = set()
for a, b, _ in WIRES0:
    for c, r in (a, b):
        if r == G.T_TOP and G.T_COL0 <= c < G.T_COL0 + len(G.TOP_PINS):
            APPROACH.add((c, r - 1))
        if r == G.T_BOT and G.T_COL0 <= c < G.T_COL0 + len(G.BOT_PINS):
            APPROACH.add((c, r + 1))

BUS_H, BUS_V = set(), set()                    # bare copper: crossable at right angles only
for _, row, (c0, c1), *_ in G.BUSES:
    BUS_H.update(run(c0, row, c1, row))
for c, r0, r1, *_ in G.SPINES:
    BUS_V.update(run(c, r0, c, r1))

H, V = 1, 2
STEP, BEND, X_BUS, X_WIRE, UNDER = 1.0, 2.5, 1.5, 6.0, 3.0


def route(a, goal, used, taken):
    """Shortest right-angle path from a to any hole in `goal`."""
    best = {(a, 0): 0.0}
    prev = {}
    pq = [(0.0, a, 0)]
    while pq:
        cost, u, o_in = heapq.heappop(pq)
        if u in goal and u != a:
            path, s = [u], (u, o_in)
            while s in prev:
                s = prev[s]
                path.append(s[0])
            return cost, path[::-1]
        if cost > best.get((u, o_in), 1e9):
            continue
        straight_only = u != a and (u in BUS_H or u in BUS_V or u in used or u in APPROACH)
        for dc, dr, o in ((1, 0, H), (-1, 0, H), (0, 1, V), (0, -1, V)):
            if straight_only and o != o_in:
                continue
            v = (u[0] + dc, u[1] + dr)
            if not (LO <= v[0] <= HI and LO <= v[1] <= HI):
                continue
            c = STEP + (BEND if o_in and o != o_in else 0.0)
            if v not in goal:
                if v in BLOCK or v in taken:
                    continue
                if v in BUS_H:
                    if o == H:
                        continue
                    c += X_BUS
                if v in BUS_V:
                    if o == V:
                        continue
                    c += X_BUS
                if v in used:
                    if any(x == o for x in used[v]):
                        continue
                    c += X_WIRE
                if v in BODY:
                    c += UNDER
            elif v in NET and ((v in BUS_H and o == H) or (v in BUS_V and o == V)):
                continue                       # land on a bus across it, never along it
            nc = cost + c
            if nc < best.get((v, o), 1e9):
                best[(v, o)] = nc
                prev[(v, o)] = (u, o_in)
                heapq.heappush(pq, (nc, v, o))
    return None


def corners(path):
    """Keep the ends and every bend."""
    keep = [path[0]]
    for p0, p1, p2 in zip(path, path[1:], path[2:]):
        if (p1[0] - p0[0], p1[1] - p0[1]) != (p2[0] - p1[0], p2[1] - p1[1]):
            keep.append(p1)
    keep.append(path[-1])
    return keep


def route_all(order):
    used, out, total, taken = {}, {}, 0.0, set()
    for i in order:
        a, b, _ = WIRES0[i]
        goal = targets(b) - taken - set(used)
        res = route(a, goal, used, taken)
        if res is None:
            return None, 1e9
        cost, path = res
        total += cost
        out[i] = path
        taken.add(path[-1])
        for p0, p1, p2 in zip(path, path[1:], path[2:]):
            used.setdefault(p1, []).append(H if p0[1] == p1[1] else V)
    return out, total


rng = random.Random(20261114)
base = sorted(range(len(WIRES0)), key=lambda i: abs(WIRES0[i][0][0] - WIRES0[i][1][0])
              + abs(WIRES0[i][0][1] - WIRES0[i][1][1]))
ROUTES, best_total = route_all(base)
for _ in range(300):
    order = base[:]
    rng.shuffle(order)
    r, t = route_all(order)
    if t < best_total:
        ROUTES, best_total = r, t
assert ROUTES is not None, "no order routes every wire"

# the original's rules, on the final layout: its wire list becomes the routed ends + the R5 link
G.JUMPERS = [(ROUTES[i][0], ROUTES[i][-1], WIRES0[i][2], True) for i in range(len(WIRES0))]
G.JUMPERS.append((R5_LINK[0], R5_LINK[1], I_BUS, False))
DOUBLED = G.check()

# assertions on the result
CROSS = {}
for i, path in ROUTES.items():
    a, b, _ = WIRES0[i]
    assert path[0] == a and path[-1] in targets(b) | {b}
    assert b not in NET or NET[path[-1]] == NET[b], "a wire landed on the wrong bus"
    for p0, p1 in zip(path, path[1:]):
        assert abs(p0[0] - p1[0]) + abs(p0[1] - p1[1]) == 1, "a step that is not one hole"
    for p in path[1:-1]:
        assert p not in BLOCK, f"wire {a}->{b} passes over occupied hole {p}"
        CROSS.setdefault(p, []).append(i)
WIRE_X = {p: w for p, w in CROSS.items() if len(w) > 1}
for p, w in WIRE_X.items():
    assert len(w) == 2, f"three wires meet at {p}"
NUM = {i: k + 1 for k, i in enumerate(sorted(ROUTES, key=lambda i: WIRES0[i][0][::-1]))}


def path_text(i):
    return " → ".join(f"({c}, {r})" for c, r in corners(ROUTES[i]))


if "--table" in sys.argv:
    print("| # | 경로 (꺾는 점) | 역할 |")
    print("|---|---|---|")
    for i in sorted(ROUTES, key=lambda i: NUM[i]):
        print(f"| {NUM[i]} | {path_text(i)} | {ROLES[i]} |")
    sys.exit(0)

# ------------------------------------------------------------------ drawing
W = 1180
out = []


def e(s):
    out.append(s)


e("<svg>")
e("<rect/>")
e('<text x="24" y="36" font-size="19" font-weight="bold" fill="#0f172a">'
  "신호 기판 배치도 — Teensy 4.1 소켓 기판</text>")
e(f'<text x="24" y="58" font-size="12.5" fill="#475569">[GA2] 80 × 80 mm 양면, 2.54 mm 간격: '
  f'{COLS} × {ROWS} 구멍, 가장자리 한 줄을 비워 쓰는 영역 {COLS-2*BORDER} × {ROWS-2*BORDER}. '
  "원본: docs/images/signal-board-perfboard-layout.svg (03-electrical.md §3.5.4)</text>")
e('<text x="24" y="77" font-size="12.5" fill="#475569">연결은 원본 생성기 '
  "scripts/gen_signal_board_figure.py의 데이터 그대로. "
  '<tspan font-weight="bold" fill="#be123c">팀 변경: R5 = 점퍼선 · 단자대 가로 · 피복선은 모두 뒷면, '
  "직각으로 꺾음</tspan></text>")

# ---- board, holes, margin, mounting holes, rulers
bx0, by0 = hx(1) - P, hy(1) - P
bx1, by1 = hx(COLS) + P, hy(ROWS) + P
e(f'<rect x="{bx0}" y="{by0}" width="{bx1-bx0}" height="{by1-by0}" rx="7" '
  f'fill="#fdf6e3" stroke="#a16207" stroke-width="2.5"/>')
for c in range(1, COLS + 1):
    for r in range(1, ROWS + 1):
        edge = c <= BORDER or c > COLS - BORDER or r <= BORDER or r > ROWS - BORDER
        e(f'<circle cx="{hx(c)}" cy="{hy(r)}" r="3.1" fill="{"#ebe3d2" if edge else "#d6c9a8"}"/>')
e(f'<rect x="{hx(LO)-13}" y="{hy(LO)-13}" width="{hx(HI)-hx(LO)+26}" height="{hy(HI)-hy(LO)+26}" '
  'rx="4" fill="none" stroke="#a16207" stroke-width="1.2" stroke-dasharray="5 4" opacity="0.65"/>')
for mx, my in ((bx0 + 15, by0 + 15), (bx1 - 15, by0 + 15), (bx0 + 15, by1 - 15), (bx1 - 15, by1 - 15)):
    e(f'<circle cx="{mx}" cy="{my}" r="7.5" fill="#ffffff" stroke="#a16207" stroke-width="2"/>')
e('<g font-size="9.5" fill="#92400e" text-anchor="middle">')
for c in range(1, COLS + 1):
    e(f'<text x="{hx(c)}" y="{by0-7}" font-weight="{"bold" if c % 5 == 0 else "normal"}">{c}</text>')
e("</g>")
e('<g font-size="9.5" fill="#92400e" text-anchor="end">')
for r in range(1, ROWS + 1):
    e(f'<text x="{bx0-7}" y="{hy(r)+3.5}" font-weight="{"bold" if r % 5 == 0 else "normal"}">{r}</text>')
e("</g>")


def part(d, value, a, b, kind, side, rev):
    col = "#0f766e" if value == "4.7 k" else ("#1d4ed8" if kind == "cap" else "#b91c1c")
    dash = ' stroke-dasharray="5 4"' if rev else ""
    e(f'<line x1="{hx(a[0])}" y1="{hy(a[1])}" x2="{hx(b[0])}" y2="{hy(b[1])}" stroke="{col}" '
      f'stroke-width="2.4"{dash}/>')
    cx, cy = (hx(a[0]) + hx(b[0])) / 2, (hy(a[1]) + hy(b[1])) / 2
    op = "0.55" if rev else "0.92"
    if a[0] == b[0]:
        e(f'<rect x="{cx-7}" y="{cy-15}" width="14" height="30" rx="3" fill="{col}" opacity="{op}"/>')
    else:
        e(f'<rect x="{cx-15}" y="{cy-7}" width="30" height="14" rx="3" fill="{col}" opacity="{op}"/>')
    lx, anc = (cx - 13, "end") if side == "L" else (cx + 13, "start")
    e(f'<text x="{lx}" y="{cy-2}" font-size="11" font-weight="bold" fill="{col}" text-anchor="{anc}" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{d}</text>')
    val = value.replace(" k", " kΩ") + (" 뒷면" if rev else "")
    e(f'<text x="{lx}" y="{cy+12}" font-size="10.5" fill="{col}" text-anchor="{anc}" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{val}</text>')


# ---- connector bodies first
def term_rect(c, r):
    half = (TERM_LEN - 2) / 2
    x0, x1 = hx(c) - half * P + 2, hx(c + 2) + half * P - 2
    y0, y1 = hy(r) - TERM_DEPTH / 2 * P + 2, hy(r) + TERM_DEPTH / 2 * P - 2
    return x0, y0, x1, y1


for d, c, r, up, lo, col, side in TERMS:
    x0, y0, x1, y1 = term_rect(c, r)
    e(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="4" fill="#ffffff" '
      f'fill-opacity="0.88" stroke="{col}" stroke-width="2.2"/>')
    # the wire leaves on the edge side: a small arrow out of the body
    xm = (x0 + x1) / 2
    if side == "top":
        e(f'<path d="M{xm-6} {y0-1} L{xm} {y0-9} L{xm+6} {y0-1} Z" fill="{col}"/>')
    else:
        e(f'<path d="M{xm-6} {y1+1} L{xm} {y1+9} L{xm+6} {y1+1} Z" fill="{col}"/>')
for d, c, r, col, label in G.HEADERS:
    e(f'<rect x="{hx(c)-13}" y="{hy(r)-13}" width="{2*P+26}" height="26" rx="3" fill="#ffffff" '
      f'fill-opacity="0.88" stroke="{col}" stroke-width="2.2"/>')

# ---- back-side parts (R3, R4) faint
for p in G.PARTS:
    if p[6]:
        part(*p)


# ---- wires (all on the back): drawn BEFORE the front copper, so a bus visibly passes over them
def pts(path):
    return " ".join(f"{hx(c)},{hy(r)}" for c, r in corners(path))


for i, path in ROUTES.items():
    col = WIRES0[i][2]
    e(f'<polyline points="{pts(path)}" fill="none" stroke="#ffffff" stroke-width="5.5" '
      'stroke-linejoin="round" opacity="0.9"/>')
    e(f'<polyline points="{pts(path)}" fill="none" stroke="{col}" stroke-width="2.6" '
      'stroke-linejoin="round"/>')
# wire-over-wire crossings: a small hop on the horizontal one
for p, (w1, w2) in WIRE_X.items():
    horiz = w1 if ROUTES[w1][ROUTES[w1].index(p) - 1][1] == p[1] else w2
    x, y = hx(p[0]), hy(p[1])
    e(f'<rect x="{x-7}" y="{y-3}" width="14" height="6" fill="#fdf6e3"/>')
    e(f'<path d="M{x-7} {y} A7 7 0 0 1 {x+7} {y}" fill="none" stroke="{WIRES0[horiz][2]}" stroke-width="2.6"/>')

# ---- buses, spines, stubs (bare copper)
SEGS = []                                       # every wire segment, in px, for label collisions
for path in ROUTES.values():
    cs = corners(path)
    SEGS += [((hx(p[0]), hy(p[1])), (hx(q[0]), hy(q[1]))) for p, q in zip(cs, cs[1:])]


def hits(x0, y0, x1, y1):
    for (ax, ay), (bx, by) in SEGS:
        if min(ax, bx) - 2 <= x1 and max(ax, bx) + 2 >= x0 and min(ay, by) - 2 <= y1 and max(ay, by) + 2 >= y0:
            return True
    return False


def bus_label_spot(c0, c1, row, label):
    """Right of the end, then below it, above it, left of the start: first spot no wire crosses."""
    w = 7.2 * len(label)
    y = hy(row)
    spots = [(hx(c1) + 14, y + 4, "start", hx(c1) + 14),
             (hx(c1) + 6, y + 19, "start", hx(c1) + 6),
             (hx(c1) + 6, y - 11, "start", hx(c1) + 6),
             (hx(c0) - 14, y + 4, "end", hx(c0) - 14 - w)]
    for c in range(c1 - 3, c0, -1):              # then along the bus, below and above it
        spots += [(hx(c), y + 19, "start", hx(c)), (hx(c), y - 11, "start", hx(c))]
    for lx, ly, anc, bx0 in spots:
        if not hits(bx0, ly - 10, bx0 + w, ly + 3):
            return lx, ly, anc
    return hx(c1) + 14, y + 4, "start"
BUS_NAME = {"V33T": "3.3 V (위)", "GND": "GND", "V33B": "3.3 V (아래)"}
for name, row, (c0, c1), col, _ in G.BUSES:
    e(f'<line x1="{hx(c0)}" y1="{hy(row)}" x2="{hx(c1)}" y2="{hy(row)}" stroke="{col}" stroke-width="7" '
      f'stroke-linecap="round" opacity="0.85"/>')
    label = BUS_NAME.get(name, name)
    lx, ly, anc = bus_label_spot(c0, c1, row, label)
    e(f'<text x="{lx}" y="{ly}" font-size="11.5" font-weight="bold" fill="{col}" text-anchor="{anc}"'
      f' paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{label}</text>')
for c, r0, r1, col, _ in G.SPINES:
    e(f'<line x1="{hx(c)}" y1="{hy(r0)}" x2="{hx(c)}" y2="{hy(r1)}" stroke="{col}" stroke-width="7" '
      f'stroke-linecap="round" opacity="0.85"/>')
for c, r0, r1, who, scol in G.STUBS:
    e(f'<line x1="{hx(c)}" y1="{hy(r0)}" x2="{hx(c)}" y2="{hy(r1)}" stroke="{scol}" stroke-width="4.5" '
      f'stroke-linecap="round" opacity="0.85"/>')

# ---- the Teensy
T_COL0, T_TOP, T_BOT = G.T_COL0, G.T_TOP, G.T_BOT
tx0 = hx(T_COL0) - 13
tx1 = hx(T_COL0 + len(G.TOP_PINS) - 1) + 13
e(f'<rect x="{tx0}" y="{hy(T_TOP)-13}" width="{tx1-tx0}" height="{hy(T_BOT)-hy(T_TOP)+26}" rx="5" '
  f'fill="#1e293b" fill-opacity="0.07" stroke="#1e293b" stroke-width="1.8" stroke-dasharray="7 4"/>')
USED = {(name, row) for _, name, row, _ in G.USED}
for row, pins in ((T_TOP, G.TOP_PINS), (T_BOT, G.BOT_PINS)):
    e(f'<rect x="{tx0+4}" y="{hy(row)-9}" width="{tx1-tx0-8}" height="18" rx="3" fill="#475569"/>')
    for i, _ in enumerate(pins):
        e(f'<circle cx="{hx(T_COL0+i)}" cy="{hy(row)}" r="4.2" fill="#f8fafc"/>')
mid = (hy(T_TOP) + hy(T_BOT)) / 2
e(f'<text x="{(tx0+tx1)/2}" y="{mid-6}" font-size="13" font-weight="bold" fill="#334155" '
  'text-anchor="middle">Teensy 4.1 — 암 헤더에 꽂는다 (직접 납땜하지 않음)</text>')
e(f'<text x="{(tx0+tx1)/2}" y="{mid+11}" font-size="10.5" fill="#64748b" text-anchor="middle">'
  "USB는 왼쪽, 부품면이 위. 핀 순서는 PJRC 핀 카드·Stage 0 벤치 배선과 일치</text>")
for row, pins, dy in ((T_TOP, G.TOP_PINS, 22), (T_BOT, G.BOT_PINS, -16)):
    for i, name in enumerate(pins):
        used = (name, row) in USED
        e(f'<text x="{hx(T_COL0+i)}" y="{hy(row)+dy}" font-size="{9 if used else 8.5}" '
          f'font-weight="{"bold" if used else "normal"}" fill="{"#0f172a" if used else "#64748b"}" '
          f'text-anchor="middle">{name}</text>')

# ---- front-side parts, R5 link, R6 position
for p in G.PARTS:
    if not p[6]:
        part(*p)
(lc, lr0), (_, lr1) = R5_LINK
e(f'<line x1="{hx(lc)}" y1="{hy(lr0)}" x2="{hx(lc)}" y2="{hy(lr1)}" stroke="{I_BUS}" stroke-width="4" '
  'stroke-linecap="round"/>')
e(f'<text x="{hx(lc)+10}" y="{hy(lr0+2)}" font-size="11" font-weight="bold" fill="{I_BUS}" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">R5</text>')
e(f'<text x="{hx(lc)+10}" y="{hy(lr0+2)+13}" font-size="10" fill="{I_BUS}" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">점퍼선</text>')
a6, b6 = R6_FREE
e(f'<rect x="{hx(a6[0])-6}" y="{hy(a6[1])-9}" width="{hx(b6[0])-hx(a6[0])+12}" height="18" rx="4" '
  'fill="none" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3"/>')
e(f'<text x="{(hx(a6[0]+1)+hx(b6[0]))/2}" y="{hy(a6[1])-13}" font-size="10" font-weight="bold" '
  'fill="#64748b" text-anchor="middle" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">R6 자리 (비움)</text>')

# ---- terminals and headers: pads and labels
for d, c, r, up, lo, col, side in TERMS:
    x0, y0, x1, y1 = term_rect(c, r)
    for h in G.term_holes(c, r):
        e(f'<circle cx="{hx(h[0])}" cy="{hy(h[1])}" r="4" fill="{col}"/>')
    # pin names on the board-centre side, terminal name on the edge side beside the arrow
    ly = y1 + 13 if side == "top" else y0 - 5
    for (pc, pr), name in zip(G.term_holes(c, r), (up, lo)):
        e(f'<text x="{hx(pc)}" y="{ly}" font-size="9.5" font-weight="bold" fill="{col}" '
          f'text-anchor="middle" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{name}</text>')
    ny = y0 - 4 if side == "top" else y1 + 14
    e(f'<text x="{x0+3}" y="{ny}" font-size="10.5" font-weight="bold" fill="{col}" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{d}</text>')
HEADER_KO = {"IBUS": "i-BUS 입력 ← 수신기", "PWM1": "PWM 1 · 조향", "PWM2": "PWM 2 · 구동"}
for d, c, r, col, _ in G.HEADERS:
    for i, h in enumerate(G.header_holes(c, r)):
        if i == 1:
            e(f'<circle cx="{hx(h[0])}" cy="{hy(h[1])}" r="4.5" fill="#ffffff" stroke="{col}" stroke-width="1.8"/>')
            e(f'<text x="{hx(h[0])}" y="{hy(h[1])+19}" font-size="8" font-weight="bold" fill="{col}" '
              'text-anchor="middle">n/c</text>')
        else:
            e(f'<circle cx="{hx(h[0])}" cy="{hy(h[1])}" r="4" fill="{col}"/>')
    e(f'<text x="{hx(c+1)}" y="{hy(r)-20}" font-size="10" font-weight="bold" fill="{col}" '
      f'text-anchor="middle" paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round">{HEADER_KO[d]}</text>')

# ---- wire ends (soldered) and numbers
for i, path in ROUTES.items():
    col = WIRES0[i][2]
    for c, r in (path[0], path[-1]):
        e(f'<circle cx="{hx(c)}" cy="{hy(r)}" r="3.2" fill="{col}" stroke="#ffffff" stroke-width="1.2"/>')
TEXT_HOLES = set(BLOCK) | set(WIRE_X) | BODY
for _, row, (c0, c1), *_ in G.BUSES:             # bus name labels sit just right of the bus end
    TEXT_HOLES.update((c1 + k, row) for k in range(1, 4))
for d, _, a, b, kind, side, rev in G.PARTS:      # part labels sit beside the part
    dc = -1 if side == "L" else 1
    TEXT_HOLES.update(((a[0] + dc, (a[1] + b[1]) // 2), (a[0] + dc, (a[1] + b[1]) // 2 + 1)))
LABELS = []
for i in sorted(ROUTES, key=lambda i: -len(ROUTES[i])):
    path = ROUTES[i]
    cand = path[1:-1] or path
    cand = cand + [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in zip(path, path[1:])]

    def score(pt):
        far = min([abs(pt[0] - h[0]) + abs(pt[1] - h[1]) for h in TEXT_HOLES] + [9])
        far_l = min([abs(pt[0] - q[0]) + abs(pt[1] - q[1]) for q in LABELS] + [9])
        return (min(far, 2.5) + min(far_l, 3), -abs(pt[0] - path[len(path) // 2][0])
                - abs(pt[1] - path[len(path) // 2][1]))
    best_pt = max(cand, key=score)
    LABELS.append(best_pt)
    ROUTES_LABEL = best_pt
    col = WIRES0[i][2]
    mx, my = hx(best_pt[0]) if isinstance(best_pt[0], int) else (hx(int(best_pt[0])) + P / 2), \
        hy(best_pt[1]) if isinstance(best_pt[1], int) else (hy(int(best_pt[1])) + P / 2)
    e(f'<circle cx="{mx}" cy="{my}" r="8" fill="#ffffff" stroke="{col}" stroke-width="1.6"/>')
    e(f'<text x="{mx}" y="{my+3.5}" font-size="9.5" font-weight="bold" fill="{col}" '
      f'text-anchor="middle">{NUM[i]}</text>')

# ---- pads that take a second wire
for h in sorted(DOUBLED):
    e(f'<circle cx="{hx(h[0])}" cy="{hy(h[1])}" r="9" fill="none" stroke="#be123c" stroke-width="1.6" opacity="0.75"/>')
e(f'<text x="{hx(1)}" y="{by1+22}" font-size="11" font-weight="bold" fill="#be123c">'
  f'빨간 동그라미: 소켓 패드에 전선을 하나 더 납땜하는 곳 {len(DOUBLED)}개. 한 구멍에 2개까지, 3개는 금지.</text>')

# ---- right margin: connectors and legend
SX, SY = bx1 + 18, by0 + 4
CONN = [
    ("위쪽 가장자리", None),
    ("PWR", "+5 V → Vin, GND (UBEC A)"),
    ("RELAY", "GATE → 21, SENSE → 20"),
    ("STRS", "SDA → 18, SCL → 19"),
    ("STRP", "조향각 센서 3.3 V, GND"),
    ("i-BUS", "신호 → R5 → 15, GND"),
    ("아래쪽 가장자리", None),
    ("DRVS", "홀센서 A → 0, B → 1"),
    ("DRVP", "홀센서 3.3 V, GND"),
    ("PWM 1", "신호 ← 2 → MUX M1"),
    ("PWM 2", "신호 ← 3 → MUX M2"),
]
e(f'<text x="{SX}" y="{SY}" font-size="13" font-weight="bold" fill="#0f172a">단자 · 헤더 → Teensy 핀</text>')
yy = SY + 24
for k, v in CONN:
    if v is None:
        e(f'<text x="{SX}" y="{yy}" font-size="11" font-weight="bold" fill="#92400e">{k}</text>')
    else:
        e(f'<text x="{SX}" y="{yy}" font-size="11.5" font-weight="bold" fill="#0f172a">{k}</text>')
        e(f'<text x="{SX+52}" y="{yy}" font-size="11.5" fill="#334155">{v}</text>')
    yy += 20
yy += 8
for ln in ["헤더 가운데(+5 V) = n/c:", "수신기·MUX는 UBEC B,", "이 기판은 UBEC A."]:
    e(f'<text x="{SX}" y="{yy}" font-size="11.5" fill="#7c3aed">{ln}</text>')
    yy += 17
yy += 14
e(f'<text x="{SX}" y="{yy}" font-size="13" font-weight="bold" fill="#0f172a">선 표기</text>')
yy += 24
e(f'<line x1="{SX}" y1="{yy-4}" x2="{SX+34}" y2="{yy-4}" stroke="#334155" stroke-width="7" opacity="0.85"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">맨 구리선 버스 (앞면)</text>')
yy += 22
e(f'<line x1="{SX}" y1="{yy-4}" x2="{SX+34}" y2="{yy-4}" stroke="#1d4ed8" stroke-width="4.5" opacity="0.85"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">스텁 (맨 구리선, 뒷면)</text>')
yy += 22
e(f'<polyline points="{SX},{yy-12} {SX+17},{yy-12} {SX+17},{yy+2} {SX+34},{yy+2}" fill="none" '
  'stroke="#be123c" stroke-width="2.6"/>')
e(f'<circle cx="{SX}" cy="{yy-12}" r="3.2" fill="#be123c" stroke="#fff" stroke-width="1.2"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">피복선 (뒷면), 점 = 납땜하는 끝</text>')
yy += 22
e(f'<circle cx="{SX+17}" cy="{yy-4}" r="8" fill="#fff" stroke="#be123c" stroke-width="1.6"/>')
e(f'<text x="{SX+17}" y="{yy-0.5}" font-size="9.5" font-weight="bold" fill="#be123c" text-anchor="middle">7</text>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">선 번호 (아래 목록)</text>')
yy += 22
e(f'<path d="M{SX} {yy-4} L{SX+10} {yy-4} A7 7 0 0 1 {SX+24} {yy-4} L{SX+34} {yy-4}" fill="none" '
  'stroke="#be123c" stroke-width="2.6"/>')
e(f'<line x1="{SX+17}" y1="{yy-16}" x2="{SX+17}" y2="{yy+8}" stroke="#1d4ed8" stroke-width="2.6"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">선끼리 교차 (닿지 않음)</text>')
yy += 22
e(f'<path d="M{SX+11} {yy-1} L{SX+17} {yy-9} L{SX+23} {yy-1} Z" fill="#dc2626"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">단자대 전선이 나가는 쪽</text>')
yy += 22
e(f'<text x="{SX}" y="{yy}" font-size="11.5" fill="#334155">피복선이 버스 아래로 지나가는 곳은</text>')
yy += 17
e(f'<text x="{SX}" y="{yy}" font-size="11.5" fill="#334155">뒷면에서 버스와 직각으로 교차</text>')


# ---- panels
def panel(x, y, w, fill, stroke, title, tcol, lines, lcol, fs=12, ls=18):
    h = 52 + ls * len(lines) + 12
    e(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    e(f'<text x="{x+20}" y="{y+30}" font-size="14" font-weight="bold" fill="{tcol}">{title}</text>')
    for i, ln in enumerate(lines):
        ln = " " * (len(ln) - len(ln.lstrip(" "))) * 2 + ln.lstrip(" ")
        e(f'<text x="{x+20}" y="{y+56+i*ls}" font-size="{fs}" fill="{lcol}">{G.rich(ln)}</text>')
    return y + h


y = by1 + 44
# wire list, two columns
order = sorted(ROUTES, key=lambda i: NUM[i])
half = (len(order) + 1) // 2
LS = 19
ph = 52 + LS * half + 12
e(f'<rect x="24" y="{y}" width="1132" height="{ph}" rx="8" fill="#f8fafc" stroke="#64748b" stroke-width="2"/>')
e(f'<text x="44" y="{y+30}" font-size="14" font-weight="bold" fill="#0f172a">피복선 목록 — 모두 뒷면, '
  "괄호는 (열, 행). 처음과 끝만 납땜하고 가운데 점에서 직각으로 꺾는다</text>")
for k, i in enumerate(order):
    a, b, col = WIRES0[i]
    x0 = 44 + (k // half) * 560
    yy = y + 56 + (k % half) * LS
    e(f'<circle cx="{x0+8}" cy="{yy-4}" r="8" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
    e(f'<text x="{x0+8}" y="{yy-0.5}" font-size="9.5" font-weight="bold" fill="{col}" text-anchor="middle">{NUM[i]}</text>')
    e(f'<text x="{x0+24}" y="{yy}" font-size="11.5" fill="#0f172a">{path_text(i)}</text>')
    e(f'<text x="{x0+548}" y="{yy}" font-size="11.5" fill="{col}" font-weight="bold" '
      f'text-anchor="end">{ROLES[i]}</text>')
y = y + ph

y = panel(24, y + 16, 1132, "#fff1f2", "#be123c", "팀 변경 사항 — 원본 배치도와 다른 점", "#881337", [
    "**R5 = 점퍼선, R6 생략.** FS-iA6B i-BUS 신호 대기 전압 3.3 V 측정(2026-11-14) → 03-electrical.md §3.5.4 표의 3.3 V 경우. "
    "R6 구멍은 비워 둔다.",
    "**피복선은 모두 뒷면, 직각으로 꺾음.** 선 끝이 모두 소켓·단자·헤더 핀인데, 앞면 패드는 플라스틱 몸체 아래라 인두가 닿지 않는다. "
    "연결은 원본과 같다.",
    "**단자대 가로.** 두 핀을 같은 행에 두어 전선이 기판 바깥(▲▼)으로 나가게 했다. 원본의 위 핀 = 왼쪽 핀. "
    "몸체 4 × 3칸·핀은 가운데 줄로 가정 — 실측 후 TERM_* 수정.",
    "**버스에 붙는 선은 같은 버스의 가장 가까운 빈 구멍에.** 같은 구리선이라 전기적으로 같다. 두 3.3 V 버스는 서로 다른 선으로 본다.",
    "**핀 순서 확인.** 원본의 '핀 순서 미확인' 경고 → PJRC 핀 카드, Stage 0 벤치 배선(핀 0·1·18·19 동작 확인)과 같다.",
    "**납땜 전 확인할 것:** 실제 기판이 29 × 29 구멍·양면인지 센다. Teensy의 VUSB–VIN 패드를 잘랐는지 확인한다(04-firmware.md 13행).",
], "#9f1239")
y2 = panel(24, y + 16, 556, "#f0fdf4", "#22c55e", "납땜 순서 — 첫 단계는 부품이 아니다", "#14532d", [
    "**1.** 암 헤더 — Teensy를 꽂은 채로 양 끝 핀만 먼저 납땜해 수평 확인.",
    "**2.** 앞면 버스 3개와 GND 세로선을 **끊김 없는 맨 구리선**으로.",
    "**3.** 뒷면 스텁(핀 0·1·18·19, R5 노드).",
    "**4.** 부품: R1·R2·C1·C2 앞면, **R3·R4 뒷면**, **R5 자리에 점퍼선.**",
    "**5.** 가장자리에 단자·헤더.",
    "**6.** 뒷면 피복선 — 목록 순서대로, 몇 가닥마다 도통 검사.",
    "**7.** Teensy를 **뺀 채로** 단락·도통 검사. 마지막에 Teensy를 꽂는다.",
], "#166534")
panel(600, y + 16, 556, "#fffbeb", "#f59e0b", "부품이 그 자리에 있는 이유", "#92400e", [
    "**3.3 V 버스 두 개는 Teensy의 3V3 핀에서** 받는다. Teensy를 뺀",
    "   기판이 0 V로 읽히는 것은 **정상**이다.",
    "**R3·R4 10 kΩ 풀업:** DRV5013 출력은 오픈 드레인. GND 버스를",
    "   건너가므로 뒷면.",
    "**C1·C2 1 nF:** 같은 두 선에서 GND로. 모터 잡음이 카운트가 되는 것을 막는다.",
    "**R1·R2 4.7 kΩ:** SCL·SDA 풀업. AS5600 보드의 풀업과 병렬.",
    "**헤더 가운데(+5 V)는 비운다** — UBEC A와 B를 잇지 않기 위해.",
], "#b45309", fs=11.5)

HH = int(max(y2, y + 16 + 52 + 18 * 7 + 12) + 30)
out[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HH}" viewBox="0 0 {W} {HH}" '
          "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
out[1] = f'<rect width="{W}" height="{HH}" fill="#ffffff"/>'
e("</svg>")

if __name__ == "__main__":
    dst = HERE / "signal_board_layout.svg"
    dst.write_text("\n".join(out), encoding="utf-8")
    nb = sum(len(corners(p)) - 2 for p in ROUTES.values())
    print(f"wrote {dst.relative_to(ROOT)}  ({len(ROUTES)} wires routed, {nb} bends, "
          f"{len(WIRE_X)} wire crossings, cost {best_total:.0f}, canvas {W}x{HH}); assertions passed")

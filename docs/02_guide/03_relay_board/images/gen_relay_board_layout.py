#!/usr/bin/env python3
"""Team (Korean) version of the relay-driver perfboard layout (GA6, 29 x 18 holes).

Usage (from the repository root):
    python3 docs/02_guide/03_relay_board/images/gen_relay_board_layout.py           # write the SVG
    python3 docs/02_guide/03_relay_board/images/gen_relay_board_layout.py --table   # wire table (markdown)

Writes relay_board_layout.svg next to this file.

WHERE THE LAYOUT COMES FROM
---------------------------
Every hole - buses, terminals, parts, the MOSFET, every wire's two ends - is READ from the
professor's generator scripts/gen_relay_board_figure.py (source of
docs/images/relay-board-perfboard-layout.svg, docs/build/03-electrical.md §3.4 and "Where it all
sits on the board"). Importing it runs its own check() and does not rewrite its SVG. Nothing here
moves a part, so the original's assertions (no two leads in one hole, pulldown ground one hole from
the source, pulldown on the gate node) are the ones that hold.

WHAT THE TEAM CHANGES
---------------------
1. EVERY insulated wire is drawn on the BACK (solder side) - the same rule as the signal board:
   every wire ends on a terminal pin, a MOSFET pin or a part lead, and a terminal's front pad is
   under its plastic body. The original already put the two wires under the TO-220 on the back.
2. The original's two diagonal wires get right-angle routes along the hole grid:
     gate -> pulldown   (14,12) -> (14,14) -> (15,14)
     sense -> terminal  (5,10) -> (3,10) -> (3,14) -> (2,14)
   Asserted: no route passes over a hole that holds anything, every crossing (bus or wire) is at a
   right angle. The sense wire cannot avoid crossing the gate wire: the gate path is row 12 from
   the terminal to the MOSFET, the sense node is above it and the SENSE pin below it.
3. Wire numbers, a wire table and Korean labels and panels.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_relay_board_figure as RB  # noqa: E402  (layout data + its check(); does not write on import)

COLS, ROWS, BORDER, P = RB.COLS, RB.ROWS, RB.BORDER, RB.P
hx, hy = RB.hx, RB.hy
LO, HI_C, HI_R = 1 + BORDER, COLS - BORDER, ROWS - BORDER
W = 1180
HALO = 'paint-order="stroke" stroke="#fdf6e3" stroke-width="3.5" stroke-linejoin="round"'

# ------------------------------------------------------------ what each wire is for
COIL = {7: "K1", 12: "K2", 17: "K3", 22: "K4"}
ROLE_BY_HOLES = {
    ((2, 4), (2, 2)): "PWR +12 V → +12 V 버스",
    ((2, 6), (4, 6)): "PWR GND → GND 세로선",
    ((2, 12), (7, 12)): "TEENSY GATE → R2",
    ((12, 12), (14, 12)): "R2 → Q1 게이트",
    ((14, 12), (15, 14)): "Q1 게이트 → R1 풀다운",
    ((15, 12), (15, 8)): "Q1 드레인 → DRAIN 버스",
    ((16, 12), (16, 17)): "Q1 소스 → GND 버스",
    ((5, 8), (5, 10)): "R3 → R4 (감지 노드)",
    ((5, 10), (2, 14)): "감지 노드 → TEENSY SENSE",
}
for c, k in COIL.items():
    ROLE_BY_HOLES[((c, 4), (c, 2))] = f"{k} 86 → +12 V 버스"
    ROLE_BY_HOLES[((c, 6), (c, 8))] = f"{k} 85 → DRAIN 버스"
WIRES = [(a, b, col) for a, b, col, _ in RB.JUMPERS]
for a, b, _ in WIRES:
    assert (a, b) in ROLE_BY_HOLES, f"the original has a wire {a}->{b} this figure does not name"

# ------------------------------------------------------------ team change 2: right-angle routes
OVERRIDE = {
    ((14, 12), (15, 14)): [(14, 12), (14, 14), (15, 14)],
    ((5, 10), (2, 14)): [(5, 10), (3, 10), (3, 14), (2, 14)],
}


def expand(corners_):
    """Corner list -> every hole along it."""
    out = [corners_[0]]
    for (c0, r0), (c1, r1) in zip(corners_, corners_[1:]):
        assert c0 == c1 or r0 == r1, f"segment {c0, r0}->{c1, r1} is not horizontal or vertical"
        dc, dr = (c1 > c0) - (c1 < c0), (r1 > r0) - (r1 < r0)
        c, r = c0, r0
        while (c, r) != (c1, r1):
            c, r = c + dc, r + dr
            out.append((c, r))
    return out


ROUTES = []
for a, b, col in WIRES:
    if a[0] != b[0] and a[1] != b[1]:
        assert (a, b) in OVERRIDE, f"diagonal wire {a}->{b} has no right-angle route"
        cs = OVERRIDE[(a, b)]
    else:
        cs = [a, b]
    assert cs[0] == a and cs[-1] == b
    ROUTES.append((cs, expand(cs), col))

# what a route may not pass over
OCC = set()
for d, _, a, b, *_ in RB.PARTS:
    OCC.update((a, b))
for d, c, r, *_ in RB.TERMINALS:
    OCC.update(((c, r), (c, r + 2)))
for pin in "gds":
    OCC.add((RB.Q1[pin], RB.Q1["row"]))
for a, b, _ in WIRES:
    OCC.update((a, b))
BUS_H = set()
for _, row, (c0, c1), *_ in RB.BUSES:
    BUS_H.update((c, row) for c in range(c0, c1 + 1))
sc, sr0, sr1 = RB.GND_SPINE
BUS_V = {(sc, r) for r in range(sr0, sr1 + 1)}


def orient(path, k):
    p, q = path[k], path[k - 1]
    return "H" if p[1] == q[1] else "V"


CROSS = {}
for i, (cs, path, _) in enumerate(ROUTES):
    for k in range(1, len(path) - 1):
        p = path[k]
        assert p not in OCC, f"wire {cs[0]}->{cs[-1]} passes over occupied hole {p}"
        o_in, o_out = orient(path, k), orient(path, k + 1)
        if p in BUS_H:
            assert o_in == o_out == "V", f"wire {cs[0]}->{cs[-1]} runs along or turns on a bus at {p}"
        if p in BUS_V:
            assert o_in == o_out == "H", f"wire {cs[0]}->{cs[-1]} runs along or turns on the spine at {p}"
        CROSS.setdefault(p, []).append((i, o_in, o_out))
WIRE_X = {}
for p, hits in CROSS.items():
    if len(hits) > 1:
        assert len(hits) == 2, f"three wires meet at {p}"
        (i1, a1, b1), (i2, a2, b2) = hits
        assert a1 == b1 and a2 == b2 and a1 != a2, f"wires cross at {p} but not at a right angle"
        WIRE_X[p] = (i1 if a1 == "H" else i2)          # the horizontal one gets the hop

# numbering: top-left first, like the signal board
NUM = {i: k + 1 for k, i in enumerate(sorted(range(len(ROUTES)), key=lambda i: ROUTES[i][0][0][::-1]))}


def path_text(cs):
    return " → ".join(f"({c}, {r})" for c, r in cs)


if "--table" in sys.argv:
    print("| # | 경로 (꺾는 점) | 역할 |")
    print("|---|---|---|")
    for i in sorted(range(len(ROUTES)), key=lambda i: NUM[i]):
        cs = ROUTES[i][0]
        print(f"| {NUM[i]} | {path_text(cs)} | {ROLE_BY_HOLES[(cs[0], cs[-1])]} |")
    sys.exit(0)

# ------------------------------------------------------------------ drawing
out = []


def e(s):
    out.append(s)


e("<svg>")
e("<rect/>")
e('<text x="24" y="36" font-size="19" font-weight="bold" fill="#0f172a">'
  "릴레이 구동 기판 배치도 — GA6 만능기판</text>")
e(f'<text x="24" y="58" font-size="12.5" fill="#475569">[GA6] 50 × 80 mm 양면, 2.54 mm 간격: '
  f'{COLS} × {ROWS} 구멍, 가장자리 한 줄을 비워 쓰는 영역 {COLS-2*BORDER} × {ROWS-2*BORDER}. '
  "원본: docs/images/relay-board-perfboard-layout.svg (03-electrical.md §3.4)</text>")
e('<text x="24" y="77" font-size="12.5" fill="#475569">구멍 위치는 원본 생성기 scripts/gen_relay_board_figure.py의 '
  '데이터 그대로. <tspan font-weight="bold" fill="#be123c">팀 변경: 피복선은 모두 뒷면 · 대각선 2가닥을 직각으로</tspan>'
  "</text>")

bx0, by0 = hx(1) - P, hy(1) - P
bx1, by1 = hx(COLS) + P, hy(ROWS) + P
e(f'<rect x="{bx0}" y="{by0}" width="{bx1-bx0}" height="{by1-by0}" rx="7" fill="#fdf6e3" '
  'stroke="#a16207" stroke-width="2.5"/>')
for c in range(1, COLS + 1):
    for r in range(1, ROWS + 1):
        edge = c <= BORDER or c > COLS - BORDER or r <= BORDER or r > ROWS - BORDER
        e(f'<circle cx="{hx(c)}" cy="{hy(r)}" r="3.1" fill="{"#ebe3d2" if edge else "#d6c9a8"}"/>')
e(f'<rect x="{hx(LO)-13}" y="{hy(LO)-13}" width="{hx(HI_C)-hx(LO)+26}" height="{hy(HI_R)-hy(LO)+26}" '
  'rx="4" fill="none" stroke="#a16207" stroke-width="1.2" stroke-dasharray="5 4" opacity="0.65"/>')
for mx, my in ((bx0 + 15, by0 + 15), (bx1 - 15, by0 + 15), (bx0 + 15, by1 - 15), (bx1 - 15, by1 - 15)):
    e(f'<circle cx="{mx}" cy="{my}" r="7.5" fill="#ffffff" stroke="#a16207" stroke-width="2"/>')
e('<g font-size="9.5" fill="#92400e" text-anchor="middle">')
for c in range(1, COLS + 1):
    e(f'<text x="{hx(c)}" y="{by0-7}" font-weight="{"bold" if c % 5 == 0 else "normal"}">{c}</text>')
e("</g>")
e('<g font-size="9.5" fill="#92400e" text-anchor="end">')
for r in range(1, ROWS + 1, 2):        # odd rows only: the edge terminals label rows 4, 6, 12, 14
    e(f'<text x="{bx0-7}" y="{hy(r)+3.5}" font-weight="{"bold" if r % 5 == 0 else "normal"}">{r}</text>')
e("</g>")

# ---- terminal bodies (front) first, so wires show over them
for d, c, r, pa, pb, col in RB.TERMINALS:
    x, y = hx(c), hy(r)
    e(f'<rect x="{x-P*1.1}" y="{y-P*0.85}" width="{P*2.2}" height="{P*2.7}" rx="4" fill="#ffffff" '
      f'fill-opacity="0.9" stroke="{col}" stroke-width="2.4"/>')

# ---- buses and the GND spine (bare tinned wire)
BUS_KO = {"V12": "+12 V (E-stop 거친 코일 전원)", "DRN": "DRAIN (코일 4개의 85)", "GND": "GND"}
for name, row, (c0, c1), col, _ in RB.BUSES:
    e(f'<line x1="{hx(c0)}" y1="{hy(row)}" x2="{hx(c1)}" y2="{hy(row)}" stroke="{col}" stroke-width="7" '
      'stroke-linecap="round" opacity="0.85"/>')
e(f'<line x1="{hx(sc)}" y1="{hy(sr0)}" x2="{hx(sc)}" y2="{hy(sr1)}" stroke="#334155" stroke-width="7" '
  'stroke-linecap="round" opacity="0.85"/>')

# ---- wires (all on the back)
for i, (cs, path, col) in enumerate(ROUTES):
    pts = " ".join(f"{hx(c)},{hy(r)}" for c, r in cs)
    e(f'<polyline points="{pts}" fill="none" stroke="#ffffff" stroke-width="5.5" stroke-linejoin="round" opacity="0.9"/>')
    e(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.8" stroke-linejoin="round"/>')
for p, horiz in WIRE_X.items():
    x, y = hx(p[0]), hy(p[1])
    e(f'<rect x="{x-7}" y="{y-3}" width="14" height="6" fill="#fdf6e3"/>')
    e(f'<path d="M{x-7} {y} A7 7 0 0 1 {x+7} {y}" fill="none" stroke="{ROUTES[horiz][2]}" stroke-width="2.8"/>')

# ---- two-lead parts (front)
for d, val, a, b, kind, side in RB.PARTS:
    x1, y1, x2, y2 = hx(a[0]), hy(a[1]), hx(b[0]), hy(b[1])
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    body = "#be123d" if kind == "res-pd" else ("#0f766e" if kind.startswith("res") else "#1e3a8a")
    e(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{body}" stroke-width="2.4"/>')
    vert = abs(y2 - y1) >= abs(x2 - x1)
    bw, bh = (13, 34) if vert else (34, 13)
    e(f'<rect x="{mx-bw/2}" y="{my-bh/2}" width="{bw}" height="{bh}" rx="3" fill="{body}" stroke="#ffffff" stroke-width="1.6"/>')
    if kind == "diode":          # cathode band at hole A, which is the +12 V bus
        e(f'<rect x="{mx-6.5}" y="{my-bh/2+3}" width="13" height="5" fill="#e2e8f0"/>')
    for xx, yy in ((x1, y1), (x2, y2)):
        e(f'<circle cx="{xx}" cy="{yy}" r="4.2" fill="{body}"/>')
    v = val.replace(" k", " kΩ") if kind.startswith("res") else val
    v = v + " Ω" if v.isdigit() else v
    if vert:
        lx = mx - 11 if side == "L" else mx + 11
        anc = "end" if side == "L" else "start"
        e(f'<text x="{lx}" y="{my-1}" font-size="11" font-weight="bold" fill="{body}" text-anchor="{anc}" {HALO}>{d}</text>')
        e(f'<text x="{lx}" y="{my+13}" font-size="10" fill="{body}" text-anchor="{anc}" {HALO}>{v}</text>')
    else:
        e(f'<text x="{mx}" y="{my-13}" font-size="11" font-weight="bold" fill="{body}" text-anchor="middle" {HALO}>{d}</text>')
        e(f'<text x="{mx}" y="{my+22}" font-size="10" fill="{body}" text-anchor="middle" {HALO}>{v}</text>')

# ---- Q1, standing upright (front)
Q1 = RB.Q1
qr = Q1["row"]
qx0, qx1 = hx(Q1["g"]) - P * 0.8, hx(Q1["s"]) + P * 0.8
e(f'<rect x="{qx0}" y="{hy(qr)-P*1.6}" width="{qx1-qx0}" height="{P*1.6}" rx="3" fill="#1f2937" stroke="#0f172a" stroke-width="2"/>')
e(f'<rect x="{qx0+4}" y="{hy(qr)-P*1.6+4}" width="{qx1-qx0-8}" height="{P*0.42}" rx="2" fill="#94a3b8"/>')
e(f'<text x="{(qx0+qx1)/2}" y="{hy(qr)-P*0.55}" font-size="10.5" font-weight="bold" fill="#ffffff" '
  'text-anchor="middle">IRLZ44N</text>')
e(f'<text x="{(qx0+qx1)/2}" y="{hy(qr)-P*1.6-8}" font-size="11" font-weight="bold" fill="#0f172a" '
  f'text-anchor="middle" {HALO}>Q1 — 방열판(탭) = 드레인</text>')
for pin, lbl in (("g", "G"), ("d", "D"), ("s", "S")):
    e(f'<circle cx="{hx(Q1[pin])}" cy="{hy(qr)}" r="5" fill="#0f172a"/>')
    e(f'<rect x="{hx(Q1[pin])-7}" y="{hy(qr)+P*0.78-11}" width="14" height="14" rx="3" fill="#fdf6e3" opacity="0.95"/>')
    e(f'<text x="{hx(Q1[pin])}" y="{hy(qr)+P*0.78}" font-size="10.5" font-weight="bold" fill="#0f172a" '
      f'text-anchor="middle">{lbl}</text>')

# ---- terminal pins and labels
TERM_KO = {"PWR": "PWR", "TEENSY": "TEENSY"}
for d, c, r, pa, pb, col in RB.TERMINALS:
    x, y = hx(c), hy(r)
    edge = c <= 3
    for yy, lbl in ((y, pa), (hy(r + 2), pb)):
        e(f'<circle cx="{x}" cy="{yy}" r="4.6" fill="{col}"/>')
        lx = x - P * 1.1 - 7 if edge else x + 9
        e(f'<text x="{lx}" y="{yy+4}" font-size="10.5" font-weight="bold" fill="{col}" '
          f'text-anchor="{"end" if edge else "start"}" {HALO}>{lbl}</text>')
    name = TERM_KO.get(d, d)
    # coil terminals: name to the upper right, clear of the 86 wire and its number
    e(f'<text x="{x-P*1.1 if edge else x+P*0.45}" y="{y-P*0.85-7}" font-size="11.5" font-weight="bold" '
      f'fill="{col}" text-anchor="start" {HALO}>{name}</text>')

# ---- bus names, right of the board
for name, row, (c0, c1), col, _ in RB.BUSES:
    e(f'<text x="{hx(c1)+16}" y="{hy(row)+4}" font-size="11.5" font-weight="bold" fill="{col}">{BUS_KO[name]}</text>')

# ---- wire ends and numbers
for i, (cs, path, col) in enumerate(ROUTES):
    for c, r in (cs[0], cs[-1]):
        e(f'<circle cx="{hx(c)}" cy="{hy(r)}" r="3.2" fill="{col}" stroke="#ffffff" stroke-width="1.2"/>')
# Where a number would sit on another label or a crossing, it is placed by hand (hole coordinates).
LABEL_AT = {
    ((2, 4), (2, 2)): (2.6, 3.0),      # right of the wire: "PWR" is on its left
    ((5, 10), (2, 14)): (3.0, 11.4),   # off the crossing with the gate wire at (3, 12)
    ((2, 12), (7, 12)): (6.0, 12.0),   # off the crossings at (3, 12) and the spine (4, 12)
    ((15, 12), (15, 8)): (15.0, 9.0),  # above the Q1 caption
}
for i, (cs, path, col) in enumerate(ROUTES):
    if (cs[0], cs[-1]) in LABEL_AT:
        lc, lr = LABEL_AT[(cs[0], cs[-1])]
        mx, my = RB.X0 + (lc - 1) * P, RB.Y0 + (lr - 1) * P
        e(f'<circle cx="{mx}" cy="{my}" r="8" fill="#ffffff" stroke="{col}" stroke-width="1.6"/>')
        e(f'<text x="{mx}" y="{my+3.5}" font-size="9.5" font-weight="bold" fill="{col}" text-anchor="middle">{NUM[i]}</text>')
        continue
    # the number sits on the middle of the longest segment
    seg = max(zip(cs, cs[1:]), key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
    mx, my = (hx(seg[0][0]) + hx(seg[1][0])) / 2, (hy(seg[0][1]) + hy(seg[1][1])) / 2
    if seg[0][1] == seg[1][1] and abs(seg[0][0] - seg[1][0]) == 2:
        mx, my = hx(seg[0][0]) + P, hy(seg[0][1]) - 12     # short horizontal: sit just above it
    e(f'<circle cx="{mx}" cy="{my}" r="8" fill="#ffffff" stroke="{col}" stroke-width="1.6"/>')
    e(f'<text x="{mx}" y="{my+3.5}" font-size="9.5" font-weight="bold" fill="{col}" text-anchor="middle">{NUM[i]}</text>')

# ---- the callout the original puts on the board: pulldown and source ground one hole apart
sx, sy = hx(Q1["s"]), hy(17)
pdx = hx(15)
for cx in (sx, pdx):
    e(f'<circle cx="{cx}" cy="{sy}" r="11" fill="none" stroke="#be123d" stroke-width="2.6"/>')
e(f'<text x="{pdx+20}" y="{sy+P+4}" font-size="12" font-weight="bold" fill="#be123d">'
  "풀다운(R1)과 소스의 GND는 한 칸 차이</text>")
e(f'<path d="M {pdx+14} {sy+6} L {pdx+22} {sy+P-9}" stroke="#be123d" stroke-width="2" fill="none"/>')

# ---- right margin: legend
SX, SY = bx1 + 20, hy(9) + 14
e(f'<text x="{SX}" y="{SY}" font-size="13" font-weight="bold" fill="#0f172a">선 표기</text>')
yy = SY + 24
e(f'<line x1="{SX}" y1="{yy-4}" x2="{SX+34}" y2="{yy-4}" stroke="#334155" stroke-width="7" opacity="0.85"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">맨 구리선 버스</text>')
yy += 22
e(f'<polyline points="{SX},{yy-12} {SX+17},{yy-12} {SX+17},{yy+2} {SX+34},{yy+2}" fill="none" stroke="#2563eb" stroke-width="2.8"/>')
e(f'<circle cx="{SX}" cy="{yy-12}" r="3.2" fill="#2563eb" stroke="#fff" stroke-width="1.2"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">피복선 (뒷면)</text>')
yy += 17
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">점 = 납땜하는 끝</text>')
yy += 22
e(f'<path d="M{SX} {yy-4} L{SX+10} {yy-4} A7 7 0 0 1 {SX+24} {yy-4} L{SX+34} {yy-4}" fill="none" stroke="#7c3aed" stroke-width="2.6"/>')
e(f'<line x1="{SX+17}" y1="{yy-16}" x2="{SX+17}" y2="{yy+8}" stroke="#2563eb" stroke-width="2.6"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">교차 (닿지 않음)</text>')
yy += 22
e(f'<rect x="{SX+11}" y="{yy-16}" width="13" height="22" rx="3" fill="#1e3a8a"/>')
e(f'<rect x="{SX+11}" y="{yy-13}" width="13" height="4" fill="#e2e8f0"/>')
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">다이오드: 흰 띠 = 캐소드</text>')
yy += 17
e(f'<text x="{SX+44}" y="{yy}" font-size="11.5" fill="#334155">(띠는 모두 +12 V 버스 쪽)</text>')


# ---- panels
def panel(x, y, w, fill, stroke, title, tcol, lines, lcol, fs=12, ls=18):
    h = 52 + ls * len(lines) + 12
    e(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    e(f'<text x="{x+20}" y="{y+30}" font-size="14" font-weight="bold" fill="{tcol}">{title}</text>')
    for i, ln in enumerate(lines):
        ln = " " * (len(ln) - len(ln.lstrip(" "))) * 2 + ln.lstrip(" ")
        e(f'<text x="{x+20}" y="{y+56+i*ls}" font-size="{fs}" fill="{lcol}">{RB.rich(ln)}</text>')
    return y + h


y = by1 + 50
order = sorted(range(len(ROUTES)), key=lambda i: NUM[i])
half = (len(order) + 1) // 2
LS = 19
ph = 52 + LS * half + 12
e(f'<rect x="24" y="{y}" width="1132" height="{ph}" rx="8" fill="#f8fafc" stroke="#64748b" stroke-width="2"/>')
e(f'<text x="44" y="{y+30}" font-size="14" font-weight="bold" fill="#0f172a">피복선 목록 — 모두 뒷면, '
  "괄호는 (열, 행). 처음과 끝만 납땜하고 가운데 점에서 직각으로 꺾는다</text>")
for k, i in enumerate(order):
    cs, _, col = ROUTES[i]
    x0 = 44 + (k // half) * 560
    yy = y + 56 + (k % half) * LS
    e(f'<circle cx="{x0+8}" cy="{yy-4}" r="8" fill="#fff" stroke="{col}" stroke-width="1.6"/>')
    e(f'<text x="{x0+8}" y="{yy-0.5}" font-size="9.5" font-weight="bold" fill="{col}" text-anchor="middle">{NUM[i]}</text>')
    e(f'<text x="{x0+24}" y="{yy}" font-size="11.5" fill="#0f172a">{path_text(cs)}</text>')
    e(f'<text x="{x0+548}" y="{yy}" font-size="11.5" fill="{col}" font-weight="bold" text-anchor="end">'
      f'{ROLE_BY_HOLES[(cs[0], cs[-1])]}</text>')
y += ph

y = panel(24, y + 16, 1132, "#fff1f2", "#be123c", "팀 변경 사항 — 원본 배치도와 다른 점 (부품·단자 위치는 그대로)", "#881337", [
    "**피복선은 모두 뒷면.** 선 끝이 모두 단자·MOSFET 핀이나 부품 다리인데, 단자의 앞면 패드는 플라스틱 몸체 아래라 인두가 닿지 않는다. "
    "원본도 TO-220 밑을 지나는 두 가닥은 뒷면으로 그렸다.",
    "**대각선 2가닥을 직각으로.** 게이트 → 풀다운은 (14, 14)에서, 감지 노드 → SENSE는 (3, 10)·(3, 14)에서 꺾는다. "
    "감지선이 게이트선과 한 번 교차하는 것은 피할 수 없다(게이트 경로가 12행 전체).",
], "#9f1239")
SIDE = [
    "**1.** GND 버스(17행), GND 세로선(4열), **R1만**. 다른 것은 아직.",
    "**2.** R1 윗다리 (15, 14) – GND 버스가 **10 kΩ**인지 잰다.",
    "   재는 것은 저항이 아니라 **납땜 두 곳과 구멍 두 개**다.",
    "**3.** +12 V 버스(2행), DRAIN 버스(8행) → Q1과 그 밑의",
    "   뒷면 선(드레인·소스·게이트→풀다운) → R2 → D1–D4.",
    "   **다이오드 띠는 모두 +12 V 버스(2행) 쪽.** 하나라도",
    "   거꾸로면 로직 배터리 단락이다.",
    "**4.** 단자 6개와 선 → 릴레이를 꽂고 게이트에 3.3 V를",
    "   주어 **딸깍 네 번**을 듣는다.",
    "**5.** 마지막에 R3·R4와 감지선. **감지 노드 전압을 재고**",
    "   (약 2.6–3.1 V) 나서야 Teensy 핀 20에 잇는다.",
]
y2 = panel(24, y + 16, 556, "#eff6ff", "#1d4ed8", "납땜 순서 (원본 그대로)", "#1e3a8a", SIDE, "#1e40af")
panel(600, y + 16, 556, "#fffbeb", "#f59e0b", "부품이 그 자리에 있는 이유", "#92400e", [
    "**R1 10 kΩ 풀다운은 MOSFET 쪽에.** 게이트 선이 끊기거나",
    "   빠져도 게이트가 GND로 묶여 코일이 꺼진다 → STOCK.",
    "**R1의 GND는 소스 GND에서 한 칸.** 코일 전류가 그 사이",
    "   구리를 지나지 않게.",
    "**R2 100 Ω:** 게이트 충전 전류를 제한해 Teensy 핀 보호.",
    "**D1–D4 1N4007:** 코일이 꺼질 때 튀는 전압을 잡는다.",
    "   없으면 MOSFET(55 V)에 약 100 V가 걸린다.",
    "**R3 10 kΩ · R4 2.7 kΩ:** 12 V 코일 전원을 약 2.6 V로",
    "   낮춰 E-stop 상태를 Teensy 핀 20에 알린다.",
    "**GND 선은 이 기판에서 하나만** (PWR → 스타 접지).",
    "   Teensy와 GND 선을 따로 잇지 않는다(접지 고리).",
], "#b45309", fs=11.5)

HH = int(max(y2, y + 16 + 52 + 18 * 11 + 12) + 30)
out[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HH}" viewBox="0 0 {W} {HH}" '
          "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
out[1] = f'<rect width="{W}" height="{HH}" fill="#ffffff"/>'
e("</svg>")

if __name__ == "__main__":
    dst = HERE / "relay_board_layout.svg"
    dst.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {dst.relative_to(ROOT)}  ({len(ROUTES)} wires, {len(WIRE_X)} wire crossings, canvas {W}x{HH}); "
          "original assertions and routing checks passed")

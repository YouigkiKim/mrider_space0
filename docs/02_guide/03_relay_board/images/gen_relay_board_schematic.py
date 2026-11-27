#!/usr/bin/env python3
"""Team (Korean) schematic of the relay-driver board, with what it connects to off the board.

Usage (from the repository root):
    python3 docs/02_guide/03_relay_board/images/gen_relay_board_schematic.py

Writes relay_board_schematic.svg next to this file.

Sources:
- docs/images/relay-driver-board.svg and docs/build/03-electrical.md §3.4 (E-stop NC (2) in the
  12 V coil feed, K1-K4 and what each switches, 86 to the feed / 85 to the drain, 1N4007 per coil,
  pulldown on the MOSFET side of the 100 ohm) and "Where it all sits on the board"
- part values and terminal names are READ from scripts/gen_relay_board_figure.py (PARTS, TERMINALS)
- signal board RELAY terminal: GATE <- Teensy pin 21, SENSE -> Teensy pin 20 (04-firmware.md pin table)
- coil current and the 1N4007 clamp: docs/build/01-bom-sourcing.md (relay driver rows)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_relay_board_figure as RB  # noqa: E402

VAL = {d: v for d, v, *_ in RB.PARTS}
assert {"R1", "R2", "R3", "R4", "D1", "D2", "D3", "D4"} <= set(VAL), "the original renamed a part"
assert [t[0] for t in RB.TERMINALS] == ["PWR", "TEENSY", "K1", "K2", "K3", "K4"]


def ohm(v):
    return v.replace(" k", " kΩ") if "k" in v else v + " Ω"


R3K = float(VAL["R3"].split()[0]) * 1000
R4K = float(VAL["R4"].split()[0]) * 1000
RATIO = R4K / (R3K + R4K)

W = 1240
o = []


def a(s):
    o.append(s)


def txt(x, y, s, cls="t", anchor="start"):
    a(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{s}</text>')


def line(x1, y1, x2, y2, cls):
    a(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')


def path(d, cls):
    a(f'<path class="{cls}" d="{d}"/>')


def dot(x, y, cls="dot"):
    a(f'<circle class="{cls}" cx="{x}" cy="{y}" r="4.5"/>')


def term(x, y, label, cls="tl", anchor="start", dx=10):
    """A terminal pin on the board edge: hollow square, its name just above the wire."""
    a(f'<rect class="term" x="{x-6}" y="{y-6}" width="12" height="12" rx="2"/>')
    txt(x + dx, y - 9, label, cls, anchor)


def res_v(x, y0, y1, name, val, cls="wr", side="L"):
    """Vertical resistor between y0 and y1 (zigzag in the middle 60 px)."""
    m = (y0 + y1) / 2
    line(x, y0, x, m - 30, cls)
    zz = " ".join(f"L{x + (8 if k % 2 else -8)} {m - 30 + 7.5 * k}" for k in range(1, 8))
    path(f"M{x} {m-30} {zz} L{x} {m+30}", cls)
    line(x, m + 30, x, y1, cls)
    if side == "L":
        txt(x - 14, m - 2, name, "pn", "end")
        txt(x - 14, m + 14, val, "pv", "end")
    else:
        txt(x + 14, m - 2, name, "pn")
        txt(x + 14, m + 14, val, "pv")


def res_h(x0, x1, y, name, val, cls="wg"):
    m = (x0 + x1) / 2
    line(x0, y, m - 30, y, cls)
    zz = " ".join(f"L{m - 30 + 7.5 * k} {y + (8 if k % 2 else -8)}" for k in range(1, 8))
    path(f"M{m-30} {y} {zz} L{m+30} {y}", cls)
    line(m + 30, y, x1, y, cls)
    txt(m, y - 16, name, "pn", "middle")
    txt(m, y + 26, val, "pv", "middle")


def diode_up(x, y0, y1, name):
    """Diode with cathode (bar) at the top y0 and anode at the bottom y1."""
    m = (y0 + y1) / 2
    line(x, y0, x, m - 12, "wd")
    path(f"M{x-11} {m+10} L{x+11} {m+10} L{x} {m-10} Z", "dio")
    line(x - 12, m - 11, x + 12, m - 11, "wd")
    line(x, m + 10, x, y1, "wd")
    txt(x + 15, m + 4, name, "pn")


a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} H_" width="{W}" height="H_" '
  "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
a("""<style>
.t{font-size:13px;fill:#1e293b}.ts{font-size:12px;fill:#475569}.tb{font-size:13.5px;font-weight:bold;fill:#0f172a}
.h1{font-size:20px;font-weight:bold;fill:#0f172a}.h2{font-size:15px;font-weight:bold;fill:#0f172a}
.pn{font-size:13px;font-weight:bold;fill:#0f172a}.pv{font-size:12px;fill:#334155}
.tl{font-size:12px;font-weight:bold;fill:#1d4ed8;paint-order:stroke;stroke:#fffbeb;stroke-width:4px;stroke-linejoin:round}.red{font-size:12.5px;font-weight:bold;fill:#b91c1c}
.grn{font-size:12.5px;font-weight:bold;fill:#15803d}.blu{font-size:12.5px;font-weight:bold;fill:#1d4ed8}
.w12{stroke:#dc2626;stroke-width:3;fill:none}.wg{stroke:#b45309;stroke-width:2.6;fill:none}
.wr{stroke:#1d4ed8;stroke-width:2.6;fill:none}.wd{stroke:#15803d;stroke-width:2.4;fill:none}
.wgnd{stroke:#334155;stroke-width:3;fill:none}.wdrn{stroke:#b45309;stroke-width:3;fill:none}
.pd{stroke:#be123c;stroke-width:2.8;fill:none}.dio{fill:#dcfce7;stroke:#15803d;stroke-width:2}
.dot{fill:#0f172a}.term{fill:#ffffff;stroke:#1d4ed8;stroke-width:2}
.board{fill:#fffbeb;stroke:#a16207;stroke-width:2;stroke-dasharray:8 5}
.box{fill:#ffffff;stroke:#334155;stroke-width:2}.coil{fill:#faf5ff;stroke:#7c3aed;stroke-width:2.2}
.mos{fill:#e2e8f0;stroke:#0f172a;stroke-width:2.2}.note{fill:#fff1f2;stroke:#be123c;stroke-width:1.8}
.panel{fill:#f8fafc;stroke:#cbd5e1;stroke-width:1.5}.wcab{stroke:#64748b;stroke-width:2;fill:none;stroke-dasharray:6 4}
</style>""")
a(f'<rect width="{W}" height="H_" fill="#ffffff"/>')

txt(30, 38, "릴레이 구동 기판 회로도 — MOSFET 하나로 릴레이 코일 4개", "h1")
txt(30, 62, "출처: 03-electrical.md §3.4, docs/images/relay-driver-board.svg · 부품 값은 scripts/gen_relay_board_figure.py에서 "
    "읽음 · 점선 상자 = 이 기판(GA6), 바깥 = 다른 곳", "ts")

# ---------------------------------------------------------------- the board outline
BX0, BY0, BX1, BY1 = 300, 100, 1120, 735
a(f'<rect class="board" x="{BX0}" y="{BY0}" width="{BX1-BX0}" height="{BY1-BY0}" rx="12"/>')
txt(BX1 - 12, BY0 + 22, "릴레이 구동 기판 (GA6, 전원 박스)", "tb", "end")

RAIL, DRN, GND = 160, 470, 700
GY = 560                        # gate row
QX0, QX1, QY0, QY1 = 500, 630, 515, 615   # Q1 body
QD = 520                        # drain / source line
GN = 470                        # gate node, the MOSFET side of R2

# ---------------------------------------------------------------- off-board: battery and E-stop
a('<rect class="box" x="24" y="128" width="130" height="62" rx="8"/>')
txt(89, 153, "로직 배터리 12 V", "tb", "middle")
txt(89, 173, "LiFePO₄ · 5 A 퓨즈", "ts", "middle")
line(154, RAIL, 190, RAIL, "w12")
# E-stop NC contact (closed while the button is released)
dot(190, RAIL)
line(190, RAIL, 238, RAIL - 16, "w12")
dot(246, RAIL)
line(246, RAIL, BX0, RAIL, "w12")
txt(218, RAIL - 28, "E-stop NC ②", "red", "middle")
txt(218, RAIL + 24, "누르면 열림", "ts", "middle")
txt(218, RAIL + 40, "→ 코일 4개 모두 꺼짐", "ts", "middle")

# PWR terminal on the board edge
term(BX0, RAIL, "PWR +12 V")
line(BX0, RAIL, 1000, RAIL, "w12")
txt(1006, RAIL + 4, "+12 V 버스", "red")

# ---------------------------------------------------------------- sense divider
SX = 350
dot(SX, RAIL)
NODE = 330
res_v(SX, RAIL, NODE, "R3", ohm(VAL["R3"]), "wr", "R")
dot(SX, NODE)
res_v(SX, NODE, GND, "R4", ohm(VAL["R4"]), "wr", "R")
dot(SX, GND)
line(BX0, NODE, SX, NODE, "wr")
term(BX0, NODE, "TEENSY SENSE")
txt(SX + 14, NODE + 34, f"감지 노드 ≈ 12 V × {R4K/1000:g}/{(R3K+R4K)/1000:g}", "ts")
txt(SX + 14, NODE + 50, f"= {12*RATIO:.2f} V (E-stop 풀림)", "ts")

# ---------------------------------------------------------------- off-board: the signal board
a('<rect class="box" x="24" y="290" width="200" height="320" rx="8"/>')
txt(124, 314, "신호 기판", "tb", "middle")
txt(124, 332, "RELAY 단자", "ts", "middle")
txt(36, NODE + 4 + 30, "SENSE → Teensy 핀 20", "blu")
txt(36, GY + 4 - 30, "GATE ← Teensy 핀 21", "blu")
path(f"M224 {NODE+30} L262 {NODE+30} L262 {NODE} L{BX0} {NODE}", "wcab")
path(f"M224 {GY-30} L262 {GY-30} L262 {GY} L{BX0} {GY}", "wcab")
txt(36, 410, "케이블 2가닥 (GATE, SENSE)", "ts")
txt(36, 428, "GND 선은 따로 없음:", "ts")
txt(36, 446, "두 기판 모두 스타 접지로", "ts")
txt(36, 464, "(접지 고리 방지)", "ts")

# ---------------------------------------------------------------- coils and diodes
COILS = [(560, "K1", "조향 A"), (670, "K2", "조향 B"), (780, "K3", "구동 A"), (890, "K4", "구동 B")]
for x, k, lead in COILS:
    dot(x, RAIL)
    line(x, RAIL, x, 228, "w12")
    txt(x - 8, 222, "86", "ts", "end")
    a(f'<rect class="coil" x="{x-26}" y="228" width="52" height="96" rx="6"/>')
    txt(x, 262, k, "pn", "middle")
    txt(x, 282, "코일", "ts", "middle")
    txt(x, 300, lead, "ts", "middle")
    txt(x - 8, 340, "85", "ts", "end")
    line(x, 324, x, DRN, "wdrn")
    dot(x, DRN)
    # flyback diode beside the coil: cathode to +12 V
    dx = x + 46
    dot(dx, RAIL)
    line(dx, RAIL, dx, 200, "wd")
    diode_up(dx, 200, 380, "D" + k[1])
    line(dx, 380, dx, 410, "wd")
    line(dx, 410, x, 410, "wd")
    dot(x, 410)
    # the K terminal pins on the board edge of the coil wiring
    a(f'<rect class="term" x="{x-6}" y="{228-14}" width="12" height="10" rx="2"/>')
    a(f'<rect class="term" x="{x-6}" y="{324+4}" width="12" height="10" rx="2"/>')
txt(978, 252, f"D1–D4 {VAL['D1']}", "grn")
txt(978, 270, "띠(캐소드) = +12 V 쪽", "ts")
txt(978, 288, "거꾸로 = 배터리 단락", "red")
txt(978, 322, "□ = K 단자", "blu")
txt(978, 340, "코일은 기판 밖 릴레이", "ts")
line(QD, DRN, 1000, DRN, "wdrn")
txt(1006, DRN + 4, "DRAIN 버스", "tb")
txt(730, DRN + 22, "코일 4개의 85를 한데 묶어 MOSFET 하나가 한꺼번에 켜고 끈다", "ts", "middle")

# ---------------------------------------------------------------- the MOSFET
line(QD, DRN, QD, QY0, "wdrn")
a(f'<rect class="mos" x="{QX0}" y="{QY0}" width="{QX1-QX0}" height="{QY1-QY0}" rx="6"/>')
txt((QX0 + QX1) / 2, QY0 + 32, "Q1 IRLZ44N", "pn", "middle")
txt((QX0 + QX1) / 2, QY0 + 52, "로직 레벨 N-MOSFET", "ts", "middle")
txt((QX0 + QX1) / 2, QY0 + 70, "탭 = 드레인", "ts", "middle")
txt(QD + 8, QY0 - 6, "D", "pn")
txt(QD + 8, QY1 + 18, "S", "pn")
txt(QX0 - 8, GY - 8, "G", "pn", "end")
line(QD, QY1, QD, GND, "wgnd")
dot(QD, GND)

# ---------------------------------------------------------------- the gate: R2 in series, R1 pulldown on the MOSFET side
term(BX0, GY, "TEENSY GATE")
line(BX0, GY, 385, GY, "wg")
res_h(385, GN - 15, GY, "R2", ohm(VAL["R2"]))
line(GN - 15, GY, QX0, GY, "wg")
dot(GN, GY)
res_v(GN, GY, GND, "R1", ohm(VAL["R1"]), "pd", "L")
dot(GN, GND)

# ---------------------------------------------------------------- GND
line(BX0, GND, 1000, GND, "wgnd")
txt(1006, GND + 4, "GND 버스", "tb")
term(BX0, GND, "PWR GND")
path(f"M{BX0} {GND} L262 {GND} L262 {GND+22}", "wgnd")
txt(30, GND + 48, "→ 스타 접지(모터 드라이버). 이 기판에서 나가는 GND 선은 이것 하나", "ts")

# ---------------------------------------------------------------- callouts
a('<rect class="note" x="660" y="545" width="290" height="78" rx="6"/>')
txt(672, 566, "R1을 가장 먼저 납땜한다.", "red")
txt(672, 585, "R2의 MOSFET 쪽(게이트 노드)에 붙는다.", "ts")
txt(672, 602, "게이트 선이 끊겨도 게이트가 GND로", "ts")
txt(672, 619, "묶여 코일이 꺼진다 → STOCK.", "ts")
a('<rect class="note" x="962" y="545" width="150" height="96" rx="6"/>')
txt(972, 566, "탭 = 드레인", "red")
txt(972, 585, "접지된 금속판에", "ts")
txt(972, 602, "그냥 고정 금지.", "ts")
txt(972, 619, "방열판 불필요", "ts")
txt(972, 636, "(0.1 W 미만)", "ts")

# ---------------------------------------------------------------- panels
y = 775


def panel(x, y, w, title, rows, fs_cls="t", ls=20):
    h = 46 + ls * len(rows) + 10
    a(f'<rect class="panel" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
    txt(x + 18, y + 28, title, "h2")
    for i, r in enumerate(rows):
        r = "\u00a0" * 2 * (len(r) - len(r.lstrip(" "))) + r.lstrip(" ")   # keep the indent
        txt(x + 18, y + 52 + i * ls, r, fs_cls)
    return y + h


y1 = panel(24, y, 590, "어떻게 동작하나", [
    "· Teensy 핀 21 HIGH(3.3 V) → Q1 켜짐 → 코일 4개에 전류(약 600 mA)",
    "  → 접점이 87(NO)로 → 모터가 MDDS30에 연결 = DBW",
    "· 핀 21 LOW → Q1 꺼짐 → 접점이 87a(NC)로 → 순정 컨트롤러 = STOCK",
    "· 아래 경우는 모두 STOCK이 된다 (기본값이 안전한 쪽):",
    "  Teensy 꺼짐·리셋 / 게이트 선 빠짐(R1이 게이트를 GND로) /",
    "  로직 전원 끊김 / E-stop 누름(코일 전원 자체가 끊김)",
    "· 감지 노드: E-stop 풀림 ≈ 2.6–3.1 V, 눌림 = 0 V → Teensy 핀 20",
])
rows = [f"{'배터리 전압':<8}   감지 노드 (× {RATIO:.3f})"]
for v, note in ((12.0, ""), (12.8, " (LiFePO₄ 공칭)"), (13.3, " (만충 휴지)"), (14.6, " (충전 중 최대)")):
    rows.append(f"· {v:4.1f} V → {v*RATIO:.2f} V{note}")
rows.append("모두 3.3 V 아래 — 그래도 핀 20에 잇기 전에 잰다")
y2 = panel(630, y, 586, f"E-stop 감지 전압 (R3 {ohm(VAL['R3'])} · R4 {ohm(VAL['R4'])})", rows)
y3 = panel(24, max(y1, y2) + 14, 1192, "릴레이가 바꾸는 선 (03-electrical.md §3.4) — 접점은 이 기판에 없다", [
    "· K1 조향 모터 A · K2 조향 모터 B · K3 구동 모터 A(병렬) · K4 구동 모터 B(병렬)",
    "· 각 릴레이: 30 = 모터 쪽(공통) · 87a(NC) = 순정 컨트롤러(STOCK) · 87(NO) = MDDS30 출력(DBW) · 85·86 = 코일",
    "· 코일 극성 약속: 86 → +12 V(E-stop 거친 전원), 85 → DRAIN. 12개 모두 같게 — 다이오드 하나만 거꾸로여도 배터리 단락",
    "· 한 쌍(K1·K2, K3·K4)의 87a·87을 서로 바꿔 물리면 STOCK은 정상인데 DBW만 반대로 돈다 — 펌웨어 부호로 고치지 말고 선을 고친다",
])
H = y3 + 20
a("</svg>")
svg = "\n".join(o).replace("H_", str(H))
if __name__ == "__main__":
    dst = HERE / "relay_board_schematic.svg"
    dst.write_text(svg, encoding="utf-8")
    print(f"wrote {dst.relative_to(ROOT)}  (canvas {W}x{H})")

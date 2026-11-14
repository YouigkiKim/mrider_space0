#!/usr/bin/env python3
"""Generate the Stage 0 bench schematic with the Teensy 4.1 drawn at its real pin positions.

Usage (from this folder):  python3 gen_stage0_bench_schematic.py stage0_bench_schematic.svg
Edit ROLE below to recolour pins for a later stage, then regenerate.

Teensy 4.1, top (component) side, USB at the top:
  left edge,  top->bottom: GND 0 1 2 3 4 5 6 7 8 9 10 11 12 3.3V 24 25 26 27 28 29 30 31 32
  right edge, top->bottom: VIN GND 3.3V 23 22 21 20 19 18 17 16 15 14 13 GND 41 40 39 38 37 36 35 34 33
(03-electrical.md §3.5.3: with USB to the LEFT the upper edge is Vin.GND.3V3.23..18 and the lower
edge GND.0.1.2..; rotating USB to the top puts the upper edge on the right.)
"""
import sys

OUT = sys.argv[1]
W, H = 1190, 1290

LEFT = ["GND", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "3.3V",
        "24", "25", "26", "27", "28", "29", "30", "31", "32"]
RIGHT = ["VIN", "GND", "3.3V", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13",
         "GND", "41", "40", "39", "38", "37", "36", "35", "34", "33"]
assert len(LEFT) == 24 and len(RIGHT) == 24

USED, LATER, LED = "used", "later", "led"
# (side, label) -> (state, short function shown inside the board)
ROLE = {
    ("L", "GND"): (USED, "GND"),
    ("L", "0"): (USED, "0 엔코더 A"),
    ("L", "1"): (USED, "1 엔코더 B"),
    ("L", "2"): (LATER, "2 조향 PWM"),
    ("L", "3"): (LATER, "3 구동 PWM"),
    ("R", "GND", 1): (USED, "GND"),
    ("R", "3.3V"): (USED, "3.3V"),
    ("R", "19"): (USED, "SCL 19"),
    ("R", "18"): (USED, "SDA 18"),
    ("R", "21"): (LATER, "릴레이 21"),
    ("R", "20"): (LATER, "E-stop 20"),
    ("R", "15"): (LATER, "i-BUS 15"),
    ("R", "13"): (LED, "LED 13"),
}

BX0, BX1 = 470, 670           # board edges
PY0, PITCH = 230, 30          # first pin y, pin pitch
LX, RX = 484, 656             # pin hole x
def py(i): return PY0 + i * PITCH

o = []
def a(s): o.append(s)

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
a('<title>Stage 0 테스트 벤치 회로도 — Teensy 4.1 실제 핀 배치 기준</title>')
a("""<style>
.w{stroke:#1f2328;stroke-width:2;fill:none}
.box{stroke:#1f2328;stroke-width:2;fill:#fff}
.chip{stroke:#1f2328;stroke-width:2;fill:#f6f8fa}
.pcb{stroke:#1f2328;stroke-width:2;fill:#e8f3ec}
.board{stroke:#8c959f;stroke-width:1.5;fill:none;stroke-dasharray:6 5}
.res{stroke:#1f2328;stroke-width:2;fill:#fff}
.dot{fill:#1f2328}
.nc{stroke:#1f2328;stroke-width:1.5;fill:#fff}
.pill{stroke:#cf222e;stroke-width:1.5;fill:#fff5f5}
.pilltx{fill:#cf222e;font-size:12px;font-weight:700;text-anchor:middle}
.t{fill:#1f2328;font-size:13px}
.ts{fill:#57606a;font-size:12px}
.tb{fill:#1f2328;font-size:14px;font-weight:700}
.h1{fill:#1f2328;font-size:20px;font-weight:700}
.pin{font-size:11px;fill:#57606a}
.pinU{font-size:11px;fill:#1a7f37;font-weight:700}
.pinL{font-size:11px;fill:#bc4c00;font-weight:700}
.pinD{font-size:11px;fill:#0969da;font-weight:700}
.hU{fill:#1a7f37;stroke:#1f2328;stroke-width:1}
.hL{fill:#ffb77a;stroke:#1f2328;stroke-width:1}
.hD{fill:#79b8ff;stroke:#1f2328;stroke-width:1}
.hN{fill:#fff;stroke:#8c959f;stroke-width:1}
.lbl{fill:#0969da;font-size:12px;font-weight:700}
.step{fill:#fff;stroke:#0969da;stroke-width:1.5}
.steptx{fill:#0969da;font-size:12px;font-weight:700;text-anchor:middle}
.mN{fill:#ffd8d3;stroke:#1f2328;stroke-width:1}
.mS{fill:#d3e3ff;stroke:#1f2328;stroke-width:1}
.mtx{fill:#1f2328;font-size:10px;text-anchor:middle}
</style>""")
a(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')

# ---- title
a('<text class="h1" x="30" y="40">Stage 0 테스트 벤치 회로도 — Teensy 4.1 실제 핀 배치 기준</text>')
a('<text class="ts" x="30" y="63">Teensy를 윗면(부품면)에서 본 모습, USB가 위쪽. 핀 위치는 실제 보드와 같다. 센서만 연결 (모터·드라이버·RC·E-stop 없음).</text>')
a('<text class="ts" x="30" y="81">원본: PJRC Teensy 4.1 핀 카드, docs/build/04-firmware.md 핀 표, docs/build/03-electrical.md §3.5.2–3.5.3</text>')

# ---- helpers
def pill(cx, y):  # y = top of pill
    a(f'<rect class="pill" x="{cx-25}" y="{y}" width="50" height="18" rx="9"/>'
      f'<text class="pilltx" x="{cx}" y="{y+13}">+3V3</text>')
def gnd(x, y):  # y = top line
    a(f'<g class="w"><line x1="{x-10}" y1="{y}" x2="{x+10}" y2="{y}"/>'
      f'<line x1="{x-6.5}" y1="{y+4}" x2="{x+6.5}" y2="{y+4}"/>'
      f'<line x1="{x-3}" y1="{y+8}" x2="{x+3}" y2="{y+8}"/></g>')
def line(x1, y1, x2, y2): a(f'<line class="w" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
def dot(x, y): a(f'<circle class="dot" cx="{x}" cy="{y}" r="4"/>')
def res_v(x, y_top, name, val, side="r"):  # body 36 tall starting at y_top
    a(f'<rect class="res" x="{x-6}" y="{y_top}" width="12" height="36"/>')
    tx = x + 14 if side == "r" else x - 14
    anc = "start" if side == "r" else "end"
    a(f'<text class="t" x="{tx}" y="{y_top+15}" text-anchor="{anc}">{name}</text>'
      f'<text class="ts" x="{tx}" y="{y_top+31}" text-anchor="{anc}">{val}</text>')
def cap_down(x, y, name, val):  # from junction y downwards, ground at end
    line(x, y, x, y + 17)
    line(x - 12, y + 17, x + 12, y + 17)
    line(x - 12, y + 24, x + 12, y + 24)
    line(x, y + 24, x, y + 36)
    gnd(x, y + 36)
    a(f'<text class="t" x="{x+14}" y="{y+22}">{name}</text>'
      f'<text class="ts" x="{x+14}" y="{y+38}">{val}</text>')
def step(cx, cy, n): a(f'<circle class="step" cx="{cx}" cy="{cy}" r="10"/><text class="steptx" x="{cx}" y="{cy+4}">{n}</text>')

# ---- breadboard outlines
a('<rect class="board" x="12" y="300" width="196" height="360" rx="10"/>')
a('<text class="ts" x="200" y="318" text-anchor="end">보드 B</text>')
a('<rect class="board" x="216" y="150" width="676" height="870" rx="10"/>')
a('<text class="ts" x="884" y="1012" text-anchor="end">보드 A — Teensy + 풀업 · 커패시터</text>')
a('<rect class="board" x="900" y="330" width="278" height="250" rx="10"/>')
a('<text class="ts" x="1170" y="572" text-anchor="end">보드 C</text>')

# ---- laptop + USB (top)
a('<rect class="box" x="500" y="96" width="140" height="44" rx="8"/>')
a('<text class="tb" x="570" y="116" text-anchor="middle">노트북</text>')
a('<text class="ts" x="570" y="132" text-anchor="middle">WSL + agent</text>')
line(570, 140, 570, 186)
a('<text class="ts" x="650" y="123">← USB: 업로드 · 통신 · 5 V 전원</text>')

# ---- Teensy board
a(f'<rect class="pcb" x="{BX0}" y="186" width="{BX1-BX0}" height="{py(23)+50-186}" rx="8"/>')
a('<rect class="chip" x="545" y="178" width="50" height="22" rx="3"/>')
a('<text class="ts" x="570" y="194" text-anchor="middle">USB</text>')
a(f'<text class="tb" x="570" y="{py(23)+36}" text-anchor="middle">Teensy 4.1</text>')
a('<text class="ts" x="570" y="770" text-anchor="middle">윗면</text>')

for side, labels in (("L", LEFT), ("R", RIGHT)):
    for i, lab in enumerate(labels):
        if side == "R" and lab == "GND":
            role = ROLE[("R", "GND", 1)] if i == 1 else None  # only the top GND is wired
        else:
            role = ROLE.get((side, lab))
        state, text = role if role else (None, lab)
        cls_h = {USED: "hU", LATER: "hL", LED: "hD"}.get(state, "hN")
        cls_t = {USED: "pinU", LATER: "pinL", LED: "pinD"}.get(state, "pin")
        x = LX if side == "L" else RX
        y = py(i)
        a(f'<circle class="{cls_h}" cx="{x}" cy="{y}" r="5"/>')
        if side == "L":
            a(f'<text class="{cls_t}" x="{x+10}" y="{y+4}">{text}</text>')
        else:
            a(f'<text class="{cls_t}" x="{x-10}" y="{y+4}" text-anchor="end">{text}</text>')

L = {lab: py(i) for i, lab in enumerate(LEFT) if lab not in ("GND",)}
L_GND = py(0)
R_VIN, R_GND, R_33 = py(0), py(1), py(2)
R_SCL, R_SDA = py(RIGHT.index("19")), py(RIGHT.index("18"))

# ================= left side: quadrature =================
y0, y1 = L["0"], L["1"]        # 260, 290
# left GND pin -> ground
line(BX0, L_GND, 440, L_GND); line(440, L_GND, 440, L_GND + 8); gnd(440, L_GND + 8)
# pin 0 -> channel A row (y=400)
A_ROW, B_ROW = 400, 590
line(BX0, y0, 350, y0); line(350, y0, 350, A_ROW); line(350, A_ROW, 190, A_ROW)
# pin 1 -> channel B row
line(BX0, y1, 385, y1); line(385, y1, 385, B_ROW); line(385, B_ROW, 190, B_ROW)
a(f'<text class="lbl" x="360" y="{y0-6}">A</text>')
a(f'<text class="lbl" x="395" y="{y1-6}">B</text>')
step(420, 345, "⑤")
# R1 / C1 on row A
dot(300, A_ROW); line(300, A_ROW, 300, A_ROW - 12); res_v(300, A_ROW - 48, "R1", "10 kΩ")
line(300, A_ROW - 48, 300, A_ROW - 58); pill(300, A_ROW - 76)
dot(250, A_ROW); cap_down(250, A_ROW, "C1", "1 nF")
# R2 / C2 on row B
dot(300, B_ROW); line(300, B_ROW, 300, B_ROW - 12); res_v(300, B_ROW - 48, "R2", "10 kΩ")
line(300, B_ROW - 48, 300, B_ROW - 58); pill(300, B_ROW - 76)
dot(250, B_ROW); cap_down(250, B_ROW, "C2", "1 nF")

# latch boxes
def latch(y_mid, name, sub, cname):
    # DRV5013 TO-92 (LPG): pin 1 VCC, 2 GND, 3 OUT, seen from the marked (narrow) face
    x0, x1 = 70, 190
    a(f'<rect class="chip" x="{x0}" y="{y_mid-28}" width="{x1-x0}" height="56" rx="6"/>')
    a(f'<text class="tb" x="{(x0+x1)//2}" y="{y_mid-3}" text-anchor="middle">{name}</text>')
    a(f'<text class="ts" x="{(x0+x1)//2}" y="{y_mid+15}" text-anchor="middle">{sub}</text>')
    # pin numbers next to the leads, outside the box
    a(f'<text class="pinD" x="101" y="{y_mid-33}">1 VCC</text>')
    a(f'<text class="pinD" x="188" y="{y_mid-33}" text-anchor="end">3 OUT →</text>')
    a(f'<text class="pinD" x="159" y="{y_mid+44}" text-anchor="end">2 GND</text>')
    line(95, y_mid - 28, 95, y_mid - 45); pill(95, y_mid - 63)
    line(165, y_mid + 28, 165, y_mid + 48); gnd(165, y_mid + 48)
    # 100 nF bypass, VCC to GND, right at the latch (03-electrical.md: "at the bracket")
    dot(95, y_mid - 38); line(95, y_mid - 38, 40, y_mid - 38)
    line(40, y_mid - 38, 40, y_mid - 8)
    line(28, y_mid - 8, 52, y_mid - 8); line(28, y_mid - 1, 52, y_mid - 1)
    line(40, y_mid - 1, 40, y_mid + 10); gnd(40, y_mid + 10)
    a(f'<text class="t" x="40" y="{y_mid+36}" text-anchor="middle">{cname}</text>')
    a(f'<text class="ts" x="40" y="{y_mid+51}" text-anchor="middle">100 nF</text>')
latch(A_ROW, "H1 DRV5013", "래치 A", "C3")
latch(B_ROW, "H2 DRV5013", "래치 B", "C4")
step(140, A_ROW - 54, "①")
step(222, A_ROW + 22, "②")
# hub magnet strip
for k in range(6):
    cls = "mN" if k % 2 == 0 else "mS"
    yy = 462 + k * 12
    a(f'<rect class="{cls}" x="24" y="{yy}" width="40" height="12"/>')
    a(f'<text class="mtx" x="44" y="{yy+10}">{"N" if k % 2 == 0 else "S"}</text>')
a('<text class="ts" x="76" y="484">← 허브 자석</text>')
a('<text class="ts" x="76" y="500">(N/S 교대)</text>')

# ================= right side: power + I2C =================
# VIN: no connect
line(BX1, R_VIN, 696, R_VIN); a(f'<circle class="nc" cx="700" cy="{R_VIN}" r="4"/>')
a(f'<text class="ts" x="712" y="{R_VIN+4}">VIN: 비움 (가이드 7.2)</text>')
# GND
line(BX1, R_GND, 720, R_GND); line(720, R_GND, 720, R_GND + 6); gnd(720, R_GND + 6)
# 3.3V source
line(BX1, R_33, 760, R_33); pill(785, R_33 - 9)
a(f'<text class="ts" x="818" y="{R_33+4}">← 공급원</text>')
# SCL (upper) and SDA (lower)
AS_X0 = 930
line(BX1, R_SCL, AS_X0, R_SCL)
line(BX1, R_SDA, AS_X0, R_SDA)
a(f'<text class="lbl" x="860" y="{R_SCL-6}" text-anchor="middle">SCL</text>')
a(f'<text class="lbl" x="860" y="{R_SDA+16}" text-anchor="middle">SDA</text>')
# R4 on SCL, upwards
dot(800, R_SCL); line(800, R_SCL, 800, R_SCL - 12); res_v(800, R_SCL - 48, "R4", "4.7 kΩ")
line(800, R_SCL - 48, 800, R_SCL - 58); pill(800, R_SCL - 76)
# R3 on SDA, downwards
dot(760, R_SDA); line(760, R_SDA, 760, R_SDA + 12); res_v(760, R_SDA + 12, "R3", "4.7 kΩ")
line(760, R_SDA + 48, 760, R_SDA + 58); pill(760, R_SDA + 58)
step(862, (R_SCL + R_SDA) // 2, "③")
# AS5600
a(f'<rect class="chip" x="{AS_X0}" y="{R_SCL-30}" width="160" height="130" rx="6"/>')
a(f'<text class="t" x="{AS_X0+8}" y="{R_SCL+5}">SCL</text>')
a(f'<text class="t" x="{AS_X0+8}" y="{R_SDA+5}">SDA</text>')
a(f'<text class="tb" x="{AS_X0+100}" y="{R_SCL+2}" text-anchor="middle">U1 AS5600</text>')
a(f'<text class="ts" x="{AS_X0+100}" y="{R_SCL+19}" text-anchor="middle">breakout</text>')
a(f'<text class="ts" x="{AS_X0+100}" y="{R_SCL+36}" text-anchor="middle">I²C 주소 0x36</text>')
yb = R_SCL + 100
a(f'<text class="t" x="{AS_X0+30}" y="{yb-8}" text-anchor="middle">VCC</text>')
a(f'<text class="t" x="{AS_X0+125}" y="{yb-8}" text-anchor="middle">GND</text>')
line(AS_X0 + 30, yb, AS_X0 + 30, yb + 16); pill(AS_X0 + 30, yb + 16)
line(AS_X0 + 125, yb, AS_X0 + 125, yb + 14); gnd(AS_X0 + 125, yb + 14)
# steering magnet
mx, my = 1140, R_SCL + 30
a(f'<path class="mN" d="M{mx} {my-22} A22 22 0 0 0 {mx} {my+22} Z"/>')
a(f'<path class="mS" d="M{mx} {my-22} A22 22 0 0 1 {mx} {my+22} Z"/>')
a(f'<text class="mtx" x="{mx-9}" y="{my+4}">N</text><text class="mtx" x="{mx+9}" y="{my+4}">S</text>')
a(f'<text class="ts" x="{mx}" y="{my-30}" text-anchor="middle">자석</text>')
step(mx, my + 40, "④")

# ================= legend =================
LY = 1040
a(f'<line x1="30" y1="{LY}" x2="1160" y2="{LY}" stroke="#d0d7de" stroke-width="1"/>')
a(f'<text class="tb" x="30" y="{LY+26}">핀 색</text>')
leg = [("hU", "지금 연결 (Stage 0)"), ("hL", "다음 단계에서 사용 — 지금은 연결 안 함"),
       ("hD", "내장 LED (연결 없음, 루프마다 깜빡임)"), ("hN", "사용 안 함")]
for k, (c, t) in enumerate(leg):
    yy = LY + 46 + k * 22
    a(f'<circle class="{c}" cx="40" cy="{yy-4}" r="5"/><text class="t" x="54" y="{yy}">{t}</text>')
a(f'<text class="t" x="30" y="{LY+146}">핀 2·3은 1500 µs, 21은 LOW로 펌웨어가 고정해 둔다.</text>')
a(f'<text class="t" x="30" y="{LY+168}">왼쪽 아래 3.3V 핀과 오른쪽 가운데 GND 핀도 같은 전원이지만 이 배치에서는 쓰지 않는다.</text>')
a(f'<text class="t" x="30" y="{LY+234}">C3·C4 100 nF는 래치 바로 옆, VCC–GND 사이 (데이터시트·§3.5.4). C1·C2 1 nF(신호)와 다른 역할.</text>')
a(f'<text class="t" x="30" y="{LY+212}">DRV5013(TO-92): 인쇄면(사다리꼴의 좁은 쪽)을 보고 다리를 아래로 두면 왼쪽부터 1 VCC · 2 GND · 3 OUT.</text>')
a(f'<text class="t" x="30" y="{LY+190}">브레드보드에서는 Teensy 양쪽의 전원 레일을 점퍼 2개로 이어 3.3 V·GND를 양쪽에 보낸다 (§3.5.3).</text>')

a(f'<text class="tb" x="640" y="{LY+26}">기호와 확인 순서 (가이드 7.3)</text>')
pill(665, LY + 36); a(f'<text class="t" x="700" y="{LY+50}">모두 오른쪽 3.3V 핀 한 곳에 연결</text>')
gnd(665, LY + 64); a(f'<text class="t" x="700" y="{LY+72}">GND, 모두 공통 · ● 연결점</text>')
steps = ["① 멀티미터: +3V3 레일 3.3 V", "② 멀티미터+자석: OUT 0↔3.3 V로 바뀌고 유지",
         "③ i2c_scan: 0x36 하나만", "④ as5600_check: AGC 40–90, wrap 없음",
         "⑤ quad_count: 허브 한 바퀴 ±36"]
for k, s in enumerate(steps):
    a(f'<text class="t" x="650" y="{LY+98+k*20}">{s}</text>')

a('</svg>')
open(OUT, "w").write("\n".join(o))
print("wrote", OUT)

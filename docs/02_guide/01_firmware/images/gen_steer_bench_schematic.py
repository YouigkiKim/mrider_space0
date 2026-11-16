#!/usr/bin/env python3
"""Steering bench schematic (firmware/steering): RC receiver and Teensy -> signal MUX -> MDDS30 -> motor.

Usage (from this folder):  python3 gen_steer_bench_schematic.py steer_bench_schematic.svg

Sources: docs/build/04-firmware.md pin table, docs/build/03-electrical.md §3.5 / §3.5.1 / §3.5.4
(signal-board-perfboard-layout.svg: PWM 1 header, R5/R6, reference designators R1-R4, C1-C2),
docs/images/rc-mux-estop.svg (receiver jobs, MUX MASTER/SLAVE/SEL/OUT, FAILMODE jumper),
docs/design/dbw.md table: MDDS30 M1 = steering gearmotor, RC1 = steering.
Teensy 4.1 drawn top view, USB up (same pin order as gen_stage0_bench_schematic.py).
"""
import sys

OUT = sys.argv[1]
W, H = 1420, 1960

LEFT = ["GND", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "3.3V",
        "24", "25", "26", "27", "28", "29", "30", "31", "32"]
RIGHT = ["VIN", "GND", "3.3V", "23", "22", "21", "20", "19", "18", "17", "16", "15", "14", "13",
         "GND", "41", "40", "39", "38", "37", "36", "35", "34", "33"]

NEW, OLD, LATER, LED = "new", "old", "later", "led"
ROLE = {
    ("L", "GND"): (OLD, "GND"), ("L", "0"): (OLD, "0 엔코더 A"), ("L", "1"): (OLD, "1 엔코더 B"),
    ("L", "2"): (NEW, "2 조향 PWM"), ("L", "3"): (LATER, "3 구동 PWM"), ("L", "3.3V"): (OLD, "3.3V"),
    ("R", "GND"): (OLD, "GND"), ("R", "3.3V"): (OLD, "3.3V"), ("R", "19"): (OLD, "SCL 19"),
    ("R", "18"): (OLD, "SDA 18"), ("R", "15"): (NEW, "i-BUS 15"), ("R", "21"): (LATER, "릴레이 21"),
    ("R", "20"): (LATER, "E-stop 20"), ("R", "13"): (LED, "LED 13"),
}

BX0, BX1 = 560, 760
PY0, PITCH = 270, 30
LX, RX = 574, 746
def py(i): return PY0 + i * PITCH

o = []
def a(s): o.append(s)

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
a('<title>조향 벤치 회로도 — RC 수신기와 Teensy에서 조향 모터까지</title>')
a("""<style>
.w{stroke:#1f2328;stroke-width:2;fill:none}
.wd{stroke:#8c959f;stroke-width:2;fill:none;stroke-dasharray:6 5}
.wp{stroke:#8250df;stroke-width:2.5;fill:none}
.wb{stroke:#0969da;stroke-width:2.5;fill:none}
.wo{stroke:#bc4c00;stroke-width:2.5;fill:none}
.wm{stroke:#cf222e;stroke-width:3;fill:none}
.box{stroke:#1f2328;stroke-width:2;fill:#fff}
.chip{stroke:#1f2328;stroke-width:2;fill:#f6f8fa}
.pcb{stroke:#1f2328;stroke-width:2;fill:#e8f3ec}
.grp{stroke:#8c959f;stroke-width:1.5;fill:none;stroke-dasharray:6 5}
.dot{fill:#1f2328}
.nc{stroke:#1f2328;stroke-width:1.5;fill:#fff}
.pill{stroke:#cf222e;stroke-width:1.5;fill:#fff5f5}
.pilltx{fill:#cf222e;font-size:12px;font-weight:700;text-anchor:middle}
.pill5{stroke:#9a6700;stroke-width:1.5;fill:#fff8c5}
.pill5tx{fill:#9a6700;font-size:12px;font-weight:700;text-anchor:middle}
.t{fill:#1f2328;font-size:13px}
.ts{fill:#57606a;font-size:12px}
.tb{fill:#1f2328;font-size:14px;font-weight:700}
.h1{fill:#1f2328;font-size:20px;font-weight:700}
.pin{font-size:11px;fill:#57606a}
.pinN{font-size:11px;fill:#1a7f37;font-weight:700}
.pinO{font-size:11px;fill:#0969da;font-weight:700}
.pinL{font-size:11px;fill:#bc4c00;font-weight:700}
.pinD{font-size:11px;fill:#0969da}
.hN{fill:#1a7f37;stroke:#1f2328;stroke-width:1}
.hO{fill:#79b8ff;stroke:#1f2328;stroke-width:1}
.hL{fill:#ffb77a;stroke:#1f2328;stroke-width:1}
.hD{fill:#ddf4ff;stroke:#0969da;stroke-width:1}
.hX{fill:#fff;stroke:#8c959f;stroke-width:1}
.lp{fill:#8250df;font-size:12px;font-weight:700}
.lb{fill:#0969da;font-size:12px;font-weight:700}
.lo{fill:#bc4c00;font-size:12px;font-weight:700}
.lm{fill:#cf222e;font-size:12px;font-weight:700}
.warn{fill:#cf222e;font-size:12px;font-weight:700}
</style>""")
a(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')

def line(x1, y1, x2, y2, cls="w"): a(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
def poly(pts, cls="w"): a(f'<polyline class="{cls}" points="{" ".join(f"{x},{y}" for x, y in pts)}"/>')
def dot(x, y): a(f'<circle class="dot" cx="{x}" cy="{y}" r="4"/>')
def gnd(x, y):
    a(f'<g class="w"><line x1="{x-10}" y1="{y}" x2="{x+10}" y2="{y}"/><line x1="{x-6.5}" y1="{y+4}" '
      f'x2="{x+6.5}" y2="{y+4}"/><line x1="{x-3}" y1="{y+8}" x2="{x+3}" y2="{y+8}"/></g>')
def pill(cx, y, txt="+3V3", c="pill"):
    a(f'<rect class="{c}" x="{cx-30}" y="{y}" width="60" height="18" rx="9"/>'
      f'<text class="{c}tx" x="{cx}" y="{y+13}">{txt}</text>')
def box(x, y, w, h, title, subs=(), cls="chip"):
    a(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
    a(f'<text class="tb" x="{x+w/2}" y="{y+22}" text-anchor="middle">{title}</text>')
    for k, s in enumerate(subs):
        a(f'<text class="ts" x="{x+w/2}" y="{y+40+k*16}" text-anchor="middle">{s}</text>')
def txt(x, y, s, cls="t", anchor="start"): a(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{s}</text>')

# ---- title
txt(30, 40, "조향 벤치 회로도 — RC 수신기·Teensy → 신호 MUX → MDDS30 → 조향 모터", "h1")
txt(30, 63, "firmware/steering 단계. Teensy는 윗면(USB 위쪽), 실제 핀 배치. Stage 0 센서 회로는 그대로 두고 조향 출력과 RC 입력을 더한다.", "ts")
txt(30, 81, "원본: 04-firmware.md 핀 표 · 03-electrical.md §3.5.1(RC·MUX), §3.5.4(신호 보드: PWM 1 헤더, R5·R6) · dbw.md(MDDS30 M1 = 조향) · rc-mux-estop.svg", "ts")

# ---- Teensy
a(f'<rect class="pcb" x="{BX0}" y="226" width="{BX1-BX0}" height="{py(23)+50-226}" rx="8"/>')
a(f'<rect class="chip" x="{(BX0+BX1)//2-25}" y="216" width="50" height="22" rx="3"/>')
txt((BX0+BX1)//2, 232, "USB", "ts", "middle")
txt((BX0+BX1)//2, py(23) + 36, "Teensy 4.1", "tb", "middle")
line((BX0+BX1)//2, 216, (BX0+BX1)//2, 196)
txt((BX0+BX1)//2 + 8, 192, "USB → 노트북 (micro-ROS agent)", "ts")
for side, labels in (("L", LEFT), ("R", RIGHT)):
    seen_gnd = 0
    for i, lab in enumerate(labels):
        role = ROLE.get((side, lab))
        if side == "R" and lab == "GND":
            seen_gnd += 1
            role = role if seen_gnd == 1 else None
        state, text = role if role else (None, lab)
        ch = {NEW: "hN", OLD: "hO", LATER: "hL", LED: "hD"}.get(state, "hX")
        ct = {NEW: "pinN", OLD: "pinO", LATER: "pinL", LED: "pinD"}.get(state, "pin")
        x = LX if side == "L" else RX
        a(f'<circle class="{ch}" cx="{x}" cy="{py(i)}" r="5"/>')
        if side == "L":
            txt(x + 10, py(i) + 4, text, ct)
        else:
            txt(x - 10, py(i) + 4, text, ct, "end")

PIN2, PIN0, PIN1 = py(3), py(1), py(2)
P15, P18, P19 = py(11), py(8), py(7)
R33, RGND = py(2), py(1)

# ---- 5 V net label (receiver + MUX run on UBEC B)
def p5(cx, y): pill(cx, y, "+5 V", "pill5")

# ---- Stage 0 parts, collapsed
line(BX0, PIN0, 540, PIN0); line(BX0, PIN1, 540, PIN1)
box(340, PIN0 - 26, 200, 74, "구동 엔코더", ("Stage 0 그대로", "R3·R4 10 kΩ, C1·C2 1 nF"), "box")
line(BX1, P19, 1010, P19); line(BX1, P18, 1010, P18)
box(1010, P19 - 28, 220, 86, "조향각 센서 AS5600", ("Stage 0 그대로 · R1·R2 4.7 kΩ", "킹핀(조향축)에 장착"), "box")
line(BX1, R33, 800, R33); pill(830, R33 - 9)
line(BX1, RGND, 790, RGND); line(790, RGND, 790, RGND + 6); gnd(790, RGND + 6)

# ---- RC receiver (top left)
RX0, RY0, RW, RH = 40, 200, 260, 190
box(RX0, RY0, RW, RH, "RC 수신기 FS-iA6B", ("5 V로 동작 · 모드 채널은 미정 [D1]",), "chip")
p5(RX0 + RW - 40, RY0 - 26); line(RX0 + RW - 40, RY0 - 8, RX0 + RW - 40, RY0)
IBY = RY0 + 70
txt(RX0 + RW - 8, IBY + 4, "i-BUS", "lb", "end")
CH1X, CH2X, CH5X = RX0 + 40, RX0 + 100, RX0 + 160
txt(CH1X, RY0 + RH - 12, "CH1", "lb", "middle")
txt(CH2X, RY0 + RH - 12, "CH2", "lo", "middle")
txt(CH5X, RY0 + RH - 12, "CH5", "lb", "middle")
line(RX0, RY0 + RH - 40, RX0 - 14, RY0 + RH - 40); gnd(RX0 - 14, RY0 + RH - 40)
# i-BUS -> over the Teensy -> R5/R6 -> pin 15
R5X0, R5Y0 = 800, P15 - 25
poly([(RX0 + RW, IBY), (320, IBY), (320, 175), (870, 175), (870, P19 - 6)], "wb")
a(f'<path class="wb" d="M870 {P19-6} A6 6 0 0 1 870 {P19+6} L870 {P18-6} A6 6 0 0 1 870 {P18+6} L870 {R5Y0}"/>')
txt(330, 168, "i-BUS (시리얼)", "lb")
a(f'<rect class="box" x="{R5X0}" y="{R5Y0}" width="130" height="50" rx="6"/>')
txt(R5X0 + 65, R5Y0 + 22, "R5 = 점퍼선", "tb", "middle")
txt(R5X0 + 65, R5Y0 + 40, "R6 생략", "ts", "middle")
line(R5X0, P15, BX1, P15, "wb")
txt(R5X0, R5Y0 + 72, "i-BUS 대기 전압 3.3 V 측정 (2026-11-14)", "warn")
txt(R5X0, R5Y0 + 88, "3.3 V → R5 = 점퍼 / 5 V였다면 R5·R6 분압", "warn")
txt(R5X0, R5Y0 + 104, "(03-electrical §3.5.4)", "ts")

# ---- signal MUX
MX0, MY0, MW, MH = 40, 500, 290, 200
box(MX0, MY0, MW, MH, "신호 MUX (Pololu #2806)", ("4채널 서보 MUX · 5 V", "FAILMODE 점퍼: 연결 안 함", "핀 배치는 아래 '앞면 배선' 그림"), "chip")
S1X, S2X, SELX, VMX = CH1X, CH2X, CH5X, MX0 + MW - 40
line(S1X, RY0 + RH, S1X, MY0, "wb"); line(CH5X, RY0 + RH, SELX, MY0, "wb")
line(CH2X, RY0 + RH, S2X, MY0, "wd")
for x, lab, c in ((S1X, "SLAVE 1", "lb"), (S2X, "SLAVE 2", "lo"), (SELX, "SEL", "lb")):
    txt(x + 5, MY0 - 8, lab, c)
p5(VMX, MY0 - 30); line(VMX, MY0 - 12, VMX, MY0); txt(VMX + 34, MY0 - 16, "VM", "ts")
line(MX0, MY0 + 30, MX0 - 14, MY0 + 30); gnd(MX0 - 14, MY0 + 30)
M1Y, M2Y = MY0 + 125, MY0 + 160
txt(MX0 + MW - 8, M1Y + 4, "MASTER 1", "lp", "end")
txt(MX0 + MW - 8, M2Y + 4, "MASTER 2", "lo", "end")
poly([(BX0, PIN2), (520, PIN2), (520, M1Y), (MX0 + MW, M1Y)], "wp")
poly([(BX0, py(4)), (505, py(4)), (505, M2Y), (MX0 + MW, M2Y)], "wd")
txt(340, M1Y - 22, "PWM 1 · steer 헤더", "lp")
txt(340, M1Y - 7, "신호·GND만 (+5 n/c)", "ts")
txt(340, M2Y + 18, "핀 3 → MASTER 2 (구동, 다음 단계)", "lo")
OUT1X, OUT2X = MX0 + 70, MX0 + 200
txt(OUT1X, MY0 + MH - 10, "OUT 1", "lp", "middle")
txt(OUT2X, MY0 + MH - 10, "OUT 2", "lo", "middle")

# ---- MDDS30
DX0, DY0, DW, DH = 40, 790, 290, 160
box(DX0, DY0, DW, DH, "모터 드라이버 MDDS30", ("R/C 모드 · DIP SW1·2=00, SW3·4=11,", "SW5=0, SW6=0, SW7·8=10"), "chip")
line(OUT1X, MY0 + MH, OUT1X, DY0, "wp"); line(OUT2X, MY0 + MH, OUT2X, DY0, "wd")
txt(OUT1X + 6, MY0 + MH + 30, "OUT 1 → RC1", "lp")
txt(OUT1X + 6, MY0 + MH + 46, "신호·GND만, 빨간 +5 선은 뽑는다", "warn")
txt(OUT1X, DY0 + 92, "RC1 조향", "lp", "middle")
txt(OUT2X, DY0 + 92, "RC2 구동", "lo", "middle")
txt(DX0 + 20, DY0 + DH - 12, "B+ / B−", "lm")
txt(DX0 + 170, DY0 + DH - 12, "M1 (Left)", "lm")
txt(DX0 + DW - 8, DY0 + 120, "M2: 다음 단계", "lo", "end")
# star ground
line(DX0 + DW, DY0 + 60, DX0 + DW + 30, DY0 + 60); gnd(DX0 + DW + 30, DY0 + 60)
txt(DX0 + DW + 48, DY0 + 66, "★ 스타 접지점", "warn")
txt(DX0 + DW + 48, DY0 + 82, "Teensy·MUX·수신기·전원 −의", "ts")
txt(DX0 + DW + 48, DY0 + 98, "GND를 이 한 점에 모은다", "ts")
# bench supply
box(40, 1010, 180, 74, "실험용 전원", ("전류 제한을 낮게", "(7–35 V 범위)"), "box")
line(70, DY0 + DH, 70, 1010, "wm"); line(100, DY0 + DH, 100, 1010, "wm")
# motor
a('<circle class="box" cx="300" cy="1045" r="40"/>')
txt(300, 1041, "조향", "tb", "middle"); txt(300, 1059, "모터", "tb", "middle")
line(220, DY0 + DH, 220, 1030, "wm"); line(220, 1030, 260, 1030, "wm")
line(250, DY0 + DH, 250, 1010, "wm")
# 5 V source note
box(1010, 760, 220, 80, "+5 V 전원", ("차량: UBEC B (전원 팀)", "벤치: 별도 5 V, GND는 공통"), "box")
p5(1120, 735)
# mechanical link motor -> AS5600
poly([(300, 1085), (300, 1110), (1250, 1110), (1250, P19 + 15), (1230, P19 + 15)], "wd")
txt(760, 1102, "기계 연결: 모터가 조향축을 돌리면 AS5600이 바퀴 각도를 잰다 → 위치 루프의 피드백", "ts", "middle")

# ---- legend
LY = 1150
a(f'<line x1="30" y1="{LY}" x2="1390" y2="{LY}" stroke="#d0d7de" stroke-width="1"/>')
txt(30, LY + 26, "핀 색", "tb")
for k, (c, s) in enumerate([("hN", "이번 단계에서 새로 연결 (핀 2 조향 PWM, 핀 15 i-BUS)"),
                            ("hO", "Stage 0에서 연결한 그대로"),
                            ("hL", "다음 단계 (핀 3 구동, 20 E-stop, 21 릴레이)"),
                            ("hX", "사용 안 함")]):
    yy = LY + 48 + k * 22
    a(f'<circle class="{c}" cx="40" cy="{yy-4}" r="5"/>'); txt(54, yy, s)
txt(520, LY + 26, "선 색", "tb")
for k, (c, s) in enumerate([("lp", "보라: 조향 펄스 (Teensy → MUX → MDDS30)"), ("lb", "파랑: RC 수신기 신호"),
                            ("lm", "빨강: 모터 전원·모터 선"), ("lo", "점선·주황: 다음 단계 (구동)")]):
    txt(520, LY + 48 + k * 22, s, c)
txt(960, LY + 26, "켜는 순서와 주의", "tb")
for k, s in enumerate(["① Teensy (1500 µs 출력 시작) → ② MUX·수신기 5 V", "→ ③ 마지막에 MDDS30 (켜질 때 펄스를 정지로 학습)",
                       "실험용 전원은 모터가 겨우 돌 만큼만 전류 제한", "FAILMODE 점퍼를 빼 두면 SEL을 잃어도 Teensy(MASTER)가 제어"]):
    txt(960, LY + 48 + k * 22, s)

# ================= signal MUX, front view wiring =================
# Pad positions measured on a photo of the BACK of the board (rcm01b), then mirrored left-right.
# Back view: right block SEL/M4..M1/OUT4..OUT1 columns sig|VM|GND(square); left block S4..S1
# columns GND(square)|VS|sig, plus a VS/GND power pair with no signal. Seen from the front,
# both blocks have the SIGNAL pin on the inside and GND on the outer edge.
PX, PY, SC = 470, 1395, 0.40          # panel origin (board top-left) and photo->drawing scale
BACK_RIGHT_EDGE, BACK_TOP = 1470, 470
def fx(x_back): return PX + (BACK_RIGHT_EDGE - x_back) * SC
def fy(y_back): return PY + (y_back - BACK_TOP) * SC
a(f'<line x1="30" y1="{PY-75}" x2="1390" y2="{PY-75}" stroke="#d0d7de" stroke-width="1"/>')
txt(30, PY - 45, "신호 MUX 앞면 배선 — 부품면을 보고, SEL이 위로 오게 들었을 때 (뒷면 사진을 좌우로 뒤집은 모습)", "tb")
txt(30, PY - 25, "규칙: 두 블록 모두 신호 핀이 보드 안쪽, GND(뒷면에서 네모 패드)가 바깥 가장자리. 가운데 핀이 + (왼쪽 블록 VM, 오른쪽 블록 VS — 서로 다른 전원선)", "ts")
a(f'<rect x="{fx(1470)}" y="{fy(470)}" width="{1370*SC}" height="{1360*SC}" rx="10" fill="#e8f3ec" stroke="#1f2328" stroke-width="2"/>')
for hx, hy in ((245, 610), (245, 1700)):
    a(f'<circle cx="{fx(hx)}" cy="{fy(hy)}" r="{40*SC*1.6}" fill="#fff" stroke="#8c959f" stroke-width="2"/>')
for ly in (525, 600):
    a(f'<rect x="{fx(440)-14}" y="{fy(ly)-7}" width="28" height="14" fill="#d0d7de" stroke="#8c959f"/>')
txt(fx(440) - 22, fy(560) + 4, "LEARN (건드리지 않음)", "ts", "end")
# FAILMODE pads
for fyb in (935, 1080):
    a(f'<circle cx="{fx(640)}" cy="{fy(fyb)}" r="9" fill="#fff" stroke="#1f2328" stroke-width="1.5"/>')
txt(fx(640), fy(1160) + 4, "FAILMODE", "ts", "middle")
txt(fx(640), fy(1160) + 20, "점퍼 꽂지 않음", "warn", "middle")
def pad(x, y, kind, state):
    # kind: sig / pos / gnd ; state: use / nc / later / off
    stroke = {"use": "#1f2328", "nc": "#cf222e", "later": "#bc4c00", "off": "#8c959f"}[state]
    fill = {"sig": "#79b8ff", "pos": "#ffb3b3", "gnd": "#57606a"}[kind] if state in ("use", "later") else "#fff"
    if kind == "gnd":
        a(f'<rect x="{x-9}" y="{y-9}" width="18" height="18" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    else:
        a(f'<circle cx="{x}" cy="{y}" r="9" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    if state == "nc":
        a(f'<line x1="{x-11}" y1="{y-11}" x2="{x+11}" y2="{y+11}" stroke="#cf222e" stroke-width="2.5"/>'
          f'<line x1="{x-11}" y1="{y+11}" x2="{x+11}" y2="{y-11}" stroke="#cf222e" stroke-width="2.5"/>')
# left block (master side): columns GND | VM | SIG from the outer edge
LBX = {"gnd": fx(1395), "pos": fx(1255), "sig": fx(1115)}
LROWS = [("SEL", 545), ("M4", 690), ("M3", 835), ("M2", 975), ("M1", 1115),
         ("OUT4", 1335), ("OUT3", 1490), ("OUT2", 1640), ("OUT1", 1780)]
LUSE = {"SEL": ("use", "use", "use"), "M1": ("use", "nc", "use"), "M2": ("later", "nc", "later"),
        "OUT1": ("use", "nc", "use"), "OUT2": ("later", "nc", "later")}
for name, yb in LROWS:
    st = LUSE.get(name, ("off", "off", "off"))
    y = fy(yb)
    pad(LBX["sig"], y, "sig", st[0]); pad(LBX["pos"], y, "pos", st[1]); pad(LBX["gnd"], y, "gnd", st[2])
    txt(LBX["sig"] + 16, y + 5, name, "tb" if name in LUSE else "ts")
txt(LBX["gnd"], fy(1225) + 4, "GND", "ts", "middle"); txt(LBX["pos"], fy(1225) + 4, "VM", "ts", "middle")
# right block (slave side): columns SIG | VS | GND toward the outer edge
RBX = {"sig": fx(455), "pos": fx(310), "gnd": fx(170)}
RROWS = [("S4", 830), ("S3", 960), ("S2", 1110), ("S1", 1250)]
RUSE = {"S1": ("use", "use", "use"), "S2": ("later", "later", "later")}
for name, yb in RROWS:
    st = RUSE.get(name, ("off", "off", "off"))
    y = fy(yb)
    pad(RBX["sig"], y, "sig", st[0]); pad(RBX["pos"], y, "pos", st[1]); pad(RBX["gnd"], y, "gnd", st[2])
    txt(RBX["sig"] - 16, y + 5, name, "tb" if name in RUSE else "ts", "end")
pad(RBX["pos"], fy(1400), "pos", "off"); pad(RBX["gnd"], fy(1400), "gnd", "off")
txt(RBX["pos"], fy(1470), "VS", "ts", "middle"); txt(RBX["gnd"], fy(1470), "GND", "ts", "middle")
txt((RBX["pos"] + RBX["gnd"]) / 2, fy(1520), "(전원 입력, 안 씀)", "ts", "middle")

# cables: left block -> left side labels, right block -> right side labels
def lcable(yb, text, sub, cls):
    y = fy(yb); x0 = LBX["gnd"] - 14
    line(x0, y, x0 - 40, y, "wp" if cls == "lp" else ("wb" if cls == "lb" else "wd"))
    txt(x0 - 48, y - 2, text, cls, "end"); txt(x0 - 48, y + 14, sub, "ts", "end")
lcable(545, "← 수신기 CH5 (3선 모두)", "신호·+5·GND → MUX 전원(VM)도 여기서 받음", "lb")
lcable(975, "← Teensy 핀 3 (다음 단계)", "신호·GND만, 가운데 비움", "lo")
lcable(1115, "← Teensy 핀 2 (신호·GND만)", "가운데 VM 핀은 비운다 ✕", "lp")
lcable(1640, "→ MDDS30 RC2 (다음 단계)", "신호·GND만", "lo")
lcable(1780, "→ MDDS30 RC1 (신호·GND만)", "가운데 VM 핀은 비운다 ✕ (빨간 선 뽑기)", "lp")
def rcable(yb, text, sub, cls):
    y = fy(yb); x0 = RBX["gnd"] + 14
    line(x0, y, x0 + 40, y, "wb" if cls == "lb" else "wd")
    txt(x0 + 48, y - 2, text, cls); txt(x0 + 48, y + 14, sub, "ts")
rcable(1110, "수신기 CH2 → (다음 단계)", "3선 모두", "lo")
rcable(1250, "수신기 CH1 → (3선 모두)", "신호·+5·GND → S쪽 전원(VS)도 여기서", "lb")

# pad legend
LX0, LY0 = 1070, 1415
txt(LX0, LY0, "패드 표시", "tb")
pad(LX0 + 10, LY0 + 26, "sig", "use"); txt(LX0 + 30, LY0 + 31, "신호 — 연결")
pad(LX0 + 10, LY0 + 54, "pos", "use"); txt(LX0 + 30, LY0 + 59, "+ (VM·VS) — 연결")
pad(LX0 + 10, LY0 + 82, "gnd", "use"); txt(LX0 + 30, LY0 + 87, "GND — 연결")
pad(LX0 + 10, LY0 + 110, "pos", "nc"); txt(LX0 + 30, LY0 + 115, "연결하면 안 됨", "warn")
pad(LX0 + 10, LY0 + 138, "sig", "later"); txt(LX0 + 30, LY0 + 143, "다음 단계 (구동)", "lo")
pad(LX0 + 10, LY0 + 166, "sig", "off"); txt(LX0 + 30, LY0 + 171, "사용 안 함", "ts")
EY = fy(1400) + 40
txt(LX0, EY, "왜 가운데 핀을 비우나:", "tb")
txt(LX0, EY + 20, "VM은 수신기의 5 V(UBEC B)를 쓴다.", "ts")
txt(LX0, EY + 38, "Teensy(UBEC A)나 MDDS30의 자체 5 V와", "ts")
txt(LX0, EY + 56, "이으면 두 전원이 맞붙는다 (03-electrical §3.5.1)", "ts")

a('</svg>')
open(OUT, "w").write("\n".join(o))
print("wrote", OUT)

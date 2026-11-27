#!/usr/bin/env python3
"""FS-iA6B receiver: port map (as seen in fs_ia6b_ports.jpg) and the bench wiring to the Teensy.

Usage (from this folder):  python3 gen_receiver_wiring.py receiver_wiring.svg

Sources:
- port map: the receiver's own label (photo fs_ia6b_ports.jpg) and the team's meter readings on
  2026-11-14 (docs/03_validation/01_firmware/02_steering_bench.md §1)
- docs/build/03-electrical.md §3.5.4 (R5/R6 table), §3.5.1 (receiver jobs), line 52 (UBEC B -> receiver)
- docs/build/04-firmware.md pin table (pin 15 = Serial3 RX, i-BUS 115200 8N1)
"""
import sys

OUT = sys.argv[1]
W, H = 1200, 860

o = []


def a(s):
    o.append(s)


def txt(x, y, s, cls="t", anchor="start"):
    a(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{s}</text>')


def line(x1, y1, x2, y2, cls):
    a(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')


def path(d, cls):
    a(f'<path class="{cls}" d="{d}"/>')


def pin(x, y, cls="pin"):
    a(f'<circle class="{cls}" cx="{x}" cy="{y}" r="7"/>')


a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
a("""<style>
.t{font-size:14px;fill:#1e293b}.ts{font-size:12px;fill:#475569}.tb{font-size:14px;font-weight:bold;fill:#0f172a}
.h1{font-size:20px;font-weight:bold;fill:#0f172a}.h2{font-size:16px;font-weight:bold;fill:#0f172a}
.lb{font-size:13px;font-weight:bold;fill:#be123c}.lp{font-size:13px;font-weight:bold;fill:#dc2626}
.lg{font-size:13px;font-weight:bold;fill:#334155}.lgw{font-size:13px;font-weight:bold;fill:#e2e8f0}.warn{font-size:13px;font-weight:bold;fill:#b45309}
.mono{font-size:13px;font-weight:bold;fill:#f8fafc;font-family:monospace}
.panel{fill:#f8fafc;stroke:#cbd5e1;stroke-width:1.5}
.face{fill:#1f2937;stroke:#0f172a;stroke-width:2}
.tag{fill:#f8fafc;stroke:#94a3b8;stroke-width:1}
.box{fill:#ffffff;stroke:#334155;stroke-width:2}
.servo{fill:none;stroke:#be123c;stroke-width:2.5}
.sens{fill:none;stroke:#94a3b8;stroke-width:2;stroke-dasharray:5 4}
.pwr{fill:none;stroke:#dc2626;stroke-width:2.5;stroke-dasharray:6 4}
.pin{fill:#e5e7eb;stroke:#0f172a;stroke-width:1.5}
.pS{fill:#fbbf24;stroke:#be123c;stroke-width:2.5}.pP{fill:#dc2626;stroke:#0f172a;stroke-width:1.5}
.pG{fill:#334155;stroke:#f8fafc;stroke-width:1.5}.pX{fill:#ffffff;stroke:#dc2626;stroke-width:2}
.wS{stroke:#be123c;stroke-width:3;fill:none}.wP{stroke:#dc2626;stroke-width:3;fill:none}
.wG{stroke:#334155;stroke-width:3;fill:none}.rf{stroke:#7c3aed;stroke-width:2;fill:none;stroke-dasharray:4 5}
.ok{fill:#f0fdf4;stroke:#22c55e;stroke-width:2}
</style>""")
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

txt(30, 38, "FS-iA6B 수신기 — 핀 구조와 벤치 연결 (firmware/steering)", "h1")
txt(30, 62, "출처: 수신기 라벨(사진 fs_ia6b_ports.jpg)과 2026-11-14 측정 · 03-electrical.md §3.5.4(R5·R6), "
    "§3.5.1(수신기 역할) · 04-firmware.md 핀 표(핀 15 = Serial3 RX)", "ts")

# ------------------------------------------------------------- ① end face
a('<rect class="panel" x="20" y="84" width="540" height="640" rx="10"/>')
txt(40, 114, "① 수신기 끝면 — 라벨을 바로 읽는 방향 (B/VCC가 위)", "h2")

FX0, FY0, FX1, FY1 = 50, 140, 530, 600
a(f'<rect class="face" x="{FX0}" y="{FY0}" width="{FX1-FX0}" height="{FY1-FY0}" rx="14"/>')
ROWS = ["B/VCC", "CH6", "CH5", "CH4", "CH3", "CH2", "PPM/CH1"]
RY0, RP = 182, 62


def ry(i):
    return RY0 + i * RP


LX, IX = 70, 290                  # label column, i-BUS column
CX = [380, 425, 470]              # channel block: three pins per row
for i, name in enumerate(ROWS):
    a(f'<rect class="tag" x="{LX}" y="{ry(i)-14}" width="96" height="26" rx="4"/>')
    txt(LX + 48, ry(i) + 5, name, "tb", "middle")
    for k, x in enumerate(CX):
        pin(x, ry(i), ["pS", "pP", "pG"][k])

# i-BUS column: SERVO on the B/VCC..CH5 rows, SENS on CH4..CH2 (the green brackets on the label)
SERVO_ROLE = [("pS", "신호", "lb"), ("pP", "+5 V", "lp"), ("pG", "GND", "lgw")]
for k, (cls, role, tcls) in enumerate(SERVO_ROLE):
    pin(IX, ry(k), cls)
    txt(IX - 16, ry(k) + 5, role, tcls, "end")
for k in range(3, 6):
    pin(IX, ry(k), "pin")
a(f'<rect class="servo" x="{IX-75}" y="{ry(0)-22}" width="98" height="{ry(2)-ry(0)+44}" rx="8"/>')
a(f'<rect class="sens" x="{IX-75}" y="{ry(3)-22}" width="98" height="{ry(5)-ry(3)+44}" rx="8"/>')
txt(IX - 26, ry(0) - 30, "i-BUS SERVO", "lb", "middle")
txt(IX - 26, ry(5) + 42, "i-BUS SENS (안 씀)", "ts", "middle")

# B/VCC row = power in
a(f'<rect class="pwr" x="{CX[0]-18}" y="{ry(0)-20}" width="{CX[2]-CX[0]+36}" height="40" rx="8"/>')
txt((CX[0] + CX[2]) / 2, FY0 - 6, "전원 5 V 입력", "lp", "middle")
for k, (lab, cls) in enumerate([("신호", "lb"), ("+", "lp"), ("GND", "lg")]):
    txt(CX[k], FY1 + 24, lab, cls, "middle")

txt(40, 664, "· 채널 블록 한 줄 = 서보 3핀: 왼쪽 신호 · 가운데 + · 오른쪽 GND (+, GND는 모든 줄 공통).", "t")
txt(40, 685, "· i-BUS는 채널 블록 왼쪽의 세로 1열: 위 3핀 SERVO, 아래 3핀 SENS.", "t")
txt(40, 706, "· CH1→MUX S1, CH2→S2, CH5→SEL은 3선 그대로 (MUX 전원 VM·VS도 이 선으로).", "warn")

# ------------------------------------------------------------- ② bench wiring
a('<rect class="panel" x="580" y="84" width="600" height="640" rx="10"/>')
txt(600, 114, "② 벤치 연결 — 선 4가닥", "h2")

# transmitter
a('<rect class="box" x="900" y="134" width="250" height="70" rx="10"/>')
txt(1025, 162, "FS-i6 송신기 (리모컨)", "tb", "middle")
txt(1025, 184, "손에 듦 · 스틱/스위치 → 전파", "ts", "middle")

# bench supply
a('<rect class="box" x="600" y="134" width="210" height="96" rx="8"/>')
txt(705, 160, "벤치 전원 5 V", "tb", "middle")
txt(705, 180, "전류 제한 0.2 A", "ts", "middle")
PSP, PSN = (640, 214), (770, 214)
pin(*PSP, "pP")
pin(*PSN, "pG")
txt(PSP[0] + 14, PSP[1] + 5, "+", "lp")
txt(PSN[0] - 14, PSN[1] + 5, "−", "lg", "end")

# receiver (simplified)
RX0, RY_0, RXW, RXH = 600, 330, 250, 250
a(f'<rect class="box" x="{RX0}" y="{RY_0}" width="{RXW}" height="{RXH}" rx="10"/>')
txt(RX0 + RXW / 2 + 30, RY_0 + 70, "FS-iA6B 수신기", "tb", "middle")
txt(RX0 + RXW / 2 + 30, RY_0 + 90, "라벨: 4.0–8.4 V DC", "ts", "middle")
# B/VCC pins (+, GND)
BP, BG = (RX0 + 40, RY_0), (RX0 + 100, RY_0)
pin(*BP, "pP")
pin(*BG, "pG")
txt(RX0 + 126, RY_0 + 28, "← B/VCC 줄", "lp")
txt(BP[0], BP[1] + 26, "+", "lp", "middle")
txt(BG[0], BG[1] + 26, "GND", "lg", "middle")
# i-BUS SERVO pins
SS, SP, SG = (RX0 + RXW, RY_0 + 150), (RX0 + RXW, RY_0 + 185), (RX0 + RXW, RY_0 + 220)
for (x, y), cls, lab, tcls in ((SS, "pS", "신호 (위)", "lb"), (SP, "pX", "+5 V (가운데)", "lp"),
                               (SG, "pG", "GND (아래)", "lg")):
    pin(x, y, cls)
    txt(x - 14, y + 5, lab, tcls, "end")
txt(RX0 + RXW - 14, RY_0 + 126, "i-BUS SERVO", "lb", "end")

# radio link
path(f"M900 190 Q 820 270 {RX0+RXW-30} {RY_0}", "rf")
txt(905, 262, "2.4 GHz (바인딩된 짝끼리만)", "ts")

# Teensy
TX0, TY0, TXW, TXH = 960, 330, 200, 250
a(f'<rect class="box" x="{TX0}" y="{TY0}" width="{TXW}" height="{TXH}" rx="10" style="fill:#f1f5f9"/>')
txt(TX0 + TXW / 2, TY0 + 26, "Teensy 4.1", "tb", "middle")
txt(TX0 + TXW / 2, TY0 + 46, "USB 전원 (노트북)", "ts", "middle")
T15, TG = (TX0, RY_0 + 150), (TX0, RY_0 + 220)
pin(*T15, "pS")
pin(*TG, "pG")
txt(TX0 + 16, T15[1] + 5, "15 (Serial3 RX)", "lb")
txt(TX0 + 16, TG[1] + 5, "GND", "lg")

# wires
path(f"M{PSP[0]} {PSP[1]} L{PSP[0]} 290 L{BP[0]} 290 L{BP[0]} {BP[1]}", "wP")
path(f"M{PSN[0]} {PSN[1]} L{PSN[0]} 300 L{BG[0]} 300 L{BG[0]} {BG[1]}", "wG")
# signal through R5 = wire link
R5X = 890
path(f"M{SS[0]} {SS[1]} L{R5X-30} {SS[1]}", "wS")
a(f'<rect x="{R5X-30}" y="{SS[1]-16}" width="60" height="32" rx="5" fill="#fff1f2" stroke="#be123c" stroke-width="2"/>')
txt(R5X, SS[1] - 1, "R5", "lb", "middle")
txt(R5X, SS[1] + 12, "점퍼선", "ts", "middle")
path(f"M{R5X+30} {SS[1]} L{T15[0]} {T15[1]}", "wS")
path(f"M{SG[0]} {SG[1]} L{TG[0]} {TG[1]}", "wG")
# +5 not connected
line(SP[0] + 10, SP[1], SP[0] + 50, SP[1], "wP")
line(SP[0] + 42, SP[1] - 8, SP[0] + 58, SP[1] + 8, "wP")
line(SP[0] + 42, SP[1] + 8, SP[0] + 58, SP[1] - 8, "wP")
txt(SP[0] + 66, SP[1] + 5, "연결 안 함", "lp")

txt(600, 616, "· 신호 + GND 2가닥이 Teensy로. 수신기 +5 V는 Teensy에 연결하지 않는다.", "t")
txt(600, 636, "· GND 공통: SERVO의 GND선 하나로 전원 −·수신기·Teensy GND가 묶인다.", "t")
txt(600, 656, "· 켜는 순서: Teensy(USB) → 수신기 5 V. 끌 때는 반대.", "t")
txt(600, 676, "· 차량에서는 수신기 전원 = UBEC B 5 V (03-electrical.md 52행).", "t")
txt(600, 702, "· R5·R6은 신호 기판의 i-BUS 레벨 자리. 3.3 V 측정 → R5 점퍼선, R6 생략.", "warn")

# ------------------------------------------------------------- ③ measured
a('<rect class="ok" x="20" y="744" width="1160" height="96" rx="10"/>')
txt(40, 772, "③ 측정 결과 (2026-11-14, 수신기 5 V · 송신기 켬 · Teensy 미연결)", "h2")
txt(40, 798, "· i-BUS SERVO: 위 = 3.3 V (신호) · 가운데 = 5 V (+) · 아래 = 0 V (GND). SENS도 위 3.3 V / 가운데 5 V.", "t")
txt(40, 820, "· Teensy 연결 후 ibus_monitor: 128–132 fr/s, bad 0, age 1–8 ms → 수신 정상. "
    "자세한 기록은 docs/03_validation/01_firmware/02_steering_bench.md", "t")

a("</svg>")
open(OUT, "w", encoding="utf-8").write("\n".join(o))
print("wrote", OUT)

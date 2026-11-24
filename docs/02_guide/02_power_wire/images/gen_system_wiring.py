#!/usr/bin/env python3
"""System wiring map: every terminal and output pin of the two boards, and where each one goes.

Usage (from the repository root):
    python3 docs/02_guide/02_power_wire/images/gen_system_wiring.py

Writes system_wiring.svg next to this file. The connections are DATA (ROWS below); edit them, never
the SVG.

Sources (the original is the authority; this only collects it per pin):
- docs/build/03-electrical.md: power tree (logic battery -> UBEC A -> Teensy VIN only; UBEC B -> receiver
  + signal MUX; 12 V direct -> relay MUX coils + contactor coil), §3.4 (E-stop: NC (1) -> contactor
  coil, NC (2) -> relay MUX coils; K1-K4 and their contacts; 86 to the feed, 85 to the drain),
  §3.5.1 (receiver i-BUS -> Teensy, CH1/CH2 -> MUX slave, CH5 -> SEL; Teensy PWM -> MUX master; MUX
  OUT -> MDDS30 RC1/RC2, signal + ground only; star ground at the driver), §3.5.2 (sensor cables),
  §3.5.4 (signal board terminals and headers), "Where it all sits on the board" (relay board)
- docs/design/sensors.md §3 (IMU on Wire1: SDA1 17, SCL1 16)
- docs/design/dbw.md §4.1 (Cytron MDDS30: Left = steering, Right = traction, RC1/RC2, DIP switches, power-up
  order) and docs/build/03-electrical.md §3.5 (R/C mode table: AN1/AN2/IN1/IN2 unused)
- team layouts: docs/02_guide/01_firmware/images/signal_board_layout_imu.svg (IMUS relabelled as soldered,
  2026-11-23), docs/02_guide/03_relay_board/images/relay_board_layout.svg
- docs/build/01-bom-sourcing.md #12 (wire: traction AWG 14, logic AWG 18-20 red/black, signal AWG 22-24)
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

# pin kinds: p = power, g = ground, s = signal, m = motor current, n = not connected on purpose
COL = {"p": "#dc2626", "g": "#334155", "s": "#2563eb", "m": "#ea580c", "n": "#94a3b8"}

# A row: source connector, destination connector, the pins pairwise in order, the cable, notes.
# (name, kind) pairs; dst pins line up with src pins one for one.
SECTIONS = [
    ("① 신호 기판 (로직 박스) — 단자·헤더 → 상대편", "#1d4ed8", [
        dict(src="PWR", src_sub="신호 기판", dst="UBEC A", dst_sub="로직 배터리 12 V 입력",
             pins=[("+5 V", "p", "5 V 출력", "p"), ("GND", "g", "GND", "g")],
             cable="2선 · 로직 AWG 18–20 (빨강/검정)",
             note=["→ Teensy Vin. UBEC A는 Teensy만 먹인다", "Teensy VUSB–VIN 패드 절단 필수"]),
        dict(src="RELAY", src_sub="신호 기판", dst="TEENSY", dst_sub="릴레이 구동 기판",
             pins=[("GATE", "s", "GATE", "s"), ("SENSE", "s", "SENSE", "s")],
             cable="2선 · 신호 AWG 22–24 · GND 선 없음",
             note=["GATE ← 핀 21, SENSE → 핀 20", "로직 박스 → 전원 박스. GND는 스타 접지로"]),
        dict(src="STRS + STRP", src_sub="신호 기판", dst="AS5600", dst_sub="킹핀 브래킷 (조향각)",
             pins=[("SDA", "s", "SDA", "s"), ("SCL", "s", "SCL", "s"), ("3.3 V", "p", "VCC", "p"),
                   ("GND", "g", "GND", "g")],
             cable="4선 케이블 약 1 m · 신호선",
             note=["SDA → 핀 18, SCL → 핀 19 (Wire, 0x36)", "3.3 V는 Teensy 3V3 핀에서 (5 V 금지)"]),
        dict(src="i-BUS", src_sub="신호 기판 3핀 헤더", dst="FS-iA6B", dst_sub="i-BUS SERVO 포트",
             pins=[("신호", "s", "위 (신호)", "s"), ("n/c", "n", "가운데 +5 V", "p"),
                   ("GND", "g", "아래 (GND)", "g")],
             cable="3선 서보 케이블",
             note=["신호 → R5 점퍼 → 핀 15 (3.3 V 측정)", "가운데 +5 V는 기판에서 연결 안 됨"]),
        dict(src="DRVS + DRVP", src_sub="신호 기판", dst="홀센서 브래킷", dst_sub="허브 (DRV5013 × 2)",
             pins=[("A", "s", "H1 OUT", "s"), ("B", "s", "H2 OUT", "s"), ("3.3 V", "p", "VCC ×2", "p"),
                   ("GND", "g", "GND ×2", "g")],
             cable="4선 케이블 약 1 m · 신호선",
             note=["A → 핀 0, B → 핀 1 (풀업·1 nF는 신호 기판)", "각 래치 VCC–GND에 100 nF (브래킷 쪽)"]),
        dict(src="PWM 1", src_sub="신호 기판 3핀 헤더", dst="M1", dst_sub="신호 MUX (Pololu 2806)",
             pins=[("신호", "s", "신호", "s"), ("n/c", "n", "VM (+5 V)", "p"), ("GND", "g", "GND", "g")],
             cable="3선 서보 케이블",
             note=["핀 2 → 조향 펄스 (MASTER 1)", "가운데는 기판에서 n/c — UBEC A·B를 잇지 않음"]),
        dict(src="PWM 2", src_sub="신호 기판 3핀 헤더", dst="M2", dst_sub="신호 MUX (Pololu 2806)",
             pins=[("신호", "s", "신호", "s"), ("n/c", "n", "VM (+5 V)", "p"), ("GND", "g", "GND", "g")],
             cable="3선 서보 케이블",
             note=["핀 3 → 구동 펄스 (MASTER 2)"]),
        dict(src="IMUP + IMUS", src_sub="신호 기판", dst="BNO085", dst_sub="IMU 보드",
             pins=[("3.3 V", "p", "VIN", "p"), ("GND", "g", "GND", "g"), ("위: SCL1", "s", "SCL", "s"),
                   ("아래: SDA1", "s", "SDA", "s")],
             cable="4선 · 수십 cm 이내 (I²C)",
             note=["SCL1 → 핀 16, SDA1 → 핀 17 (Wire1, 0x4A)", "IMUS 위·아래는 1호 기판 납땜대로 (11/23)",
                   "풀업은 IMU 보드에 있음 (SCL 10 k, SDA 5 k)"]),
    ]),
    ("② 릴레이 구동 기판 (전원 박스) — 단자 → 상대편", "#b45309", [
        dict(src="PWR", src_sub="릴레이 구동 기판", dst="E-stop NC ②", dst_sub="← 5 A 퓨즈 ← 로직 배터리 12 V",
             pins=[("+12 V", "p", "NC ② 출력", "p"), ("GND", "g", "스타 접지", "g")],
             cable="2선 · 로직 AWG 18–20 (빨강/검정)",
             note=["E-stop을 누르면 코일 4개 전원이 끊김 → STOCK", "GND 선은 이것 하나 (접지 고리 방지)"]),
        dict(src="TEENSY", src_sub="릴레이 구동 기판", dst="RELAY", dst_sub="신호 기판",
             pins=[("GATE", "s", "GATE", "s"), ("SENSE", "s", "SENSE", "s")],
             cable="① RELAY와 같은 케이블",
             note=["SENSE 약 2.6 V(12 V)·0 V(E-stop) → 핀 20", "핀 20에 잇기 전에 전압을 잰다"]),
        dict(src="K1–K4", src_sub="릴레이 구동 기판 (각 2핀)", dst="릴레이 코일", dst_sub="릴레이 소켓 K1–K4 (85·86)",
             pins=[("86", "p", "86 (+12 V 쪽)", "p"), ("85", "s", "85 (DRAIN 쪽)", "s")],
             cable="릴레이마다 2선 (× 4)",
             note=["86 → +12 V, 85 → DRAIN: 12개 모두 같게", "소켓 전선 색은 실측. 소켓에 K1–K4 표시"]),
    ]),
    ("③ 모터 드라이버 MDDS30 — 단자 → 상대편", "#9a3412", [
        dict(src="MDDS30", src_sub="Cytron SmartDriveDuo-30", dst="상대편", dst_sub="전원·릴레이 MUX·신호 MUX",
             pins=[("B+", "p", "컨택터 87 → T 분기", "p"), ("B−", "g", "팩 − (스타 접지점)", "g"),
                   ("MLA", "m", "K1 87 (조향 A)", "m"), ("MLB", "m", "K2 87 (조향 B)", "m"),
                   ("MRA", "m", "K3 87 (구동 A)", "m"), ("MRB", "m", "K4 87 (구동 B)", "m"),
                   ("RC1", "s", "MUX OUT1 (신호·GND만)", "s"), ("RC2", "s", "MUX OUT2 (신호·GND만)", "s"),
                   ("AN1·AN2·IN1·IN2", "n", "R/C 모드에서 안 씀", "n")],
             cable="트랙션 AWG 14 · RC는 3핀 (빨간 선 빼기)",
             note=["B+가 드라이버 로직 전원도 겸함 → E-stop이면 드라이버도 꺼짐",
                   "Left(MLA·MLB) = 조향 = 원본 표의 M1", "Right(MRA·MRB) = 구동 = 원본 표의 M2",
                   "DIP: SW1·2=00, SW3·4=11, SW5=0, SW6=0, SW7·8=10",
                   "켜는 순서: 수신기·Teensy·MUX 먼저, 드라이버 마지막", "B+·B−·모터 4선은 전원 팀, RC1·RC2는 Track E"]),
    ]),
    ("④ 기판을 거치지 않는 연결 — 전원 분배", "#15803d", [
        dict(src="로직 배터리", src_sub="12 V LiFePO4 → 5 A 퓨즈", dst="분배", dst_sub="퓨즈 뒤에서 세 갈래",
             pins=[("+12 V", "p", "UBEC A 입력", "p"), ("+12 V", "p", "UBEC B 입력", "p"),
                   ("+12 V", "p", "12 V 직결 → E-stop NC ①·② 입력", "p"), ("−", "g", "스타 접지", "g")],
             cable="로직 AWG 18 (퓨즈까지)",
             note=["UBEC A → Teensy만, UBEC B → 수신기·MUX만", "12 V 직결 → E-stop 거쳐 코일들 (컨택터, 릴레이 4개)",
                   "UBEC 입력 GND도 배터리 −로"]),
        dict(src="E-stop NC ①", src_sub="MRE-RR2R 버튼", dst="컨택터 코일", dst_sub="KKA-B4 (85·86)",
             pins=[("NC ① 출력", "p", "85", "p"), ("로직 GND (스타)", "g", "86", "g")],
             cable="로직 AWG 18–20",
             note=["NC ①·NC ②는 서로 다른 접점 블록에 (2a2b = 1a1b × 2)", "E-stop을 누르면 컨택터가 열려 트랙션 전원이 끊김"]),
        dict(src="트랙션 팩 · 컨택터", src_sub="AWG 14", dst="트랙션 전원", dst_sub="전원 팀",
             pins=[("팩 +", "p", "25 A 퓨즈 → 컨택터 30", "p"), ("컨택터 87", "p", "T 분기 → 순정 ECU + · MDDS30 B+", "p"),
                   ("팩 −", "g", "스타 접지 (끊지 않음)", "g")],
             cable="트랙션 AWG 14 (빨강/검정)",
             note=["T 분기는 퓨즈·컨택터 둘 다 뒤에", "로직 레일과는 스타 접지에서만 만난다"]),
        dict(src="UBEC B", src_sub="로직 배터리 12 V 입력", dst="FS-iA6B", dst_sub="B/VCC 줄",
             pins=[("5 V 출력", "p", "가운데 (+)", "p"), ("GND", "g", "GND", "g")],
             cable="2선 · 로직",
             note=["수신기와 MUX만 먹인다 (Teensy와 분리)", "UBEC A가 죽어도 수신기·MUX는 산다"]),
    ]),
    ("⑤ 기판을 거치지 않는 연결 — 신호·모터·접지", "#0f766e", [
        dict(src="FS-iA6B", src_sub="수신기 채널 포트", dst="신호 MUX", dst_sub="Pololu 2806",
             pins=[("CH1 (3선)", "s", "S1 (SLAVE 1)", "s"), ("CH2 (3선)", "s", "S2 (SLAVE 2)", "s"),
                   ("CH5 (3선)", "s", "SEL", "s")],
             cable="서보 케이블 3선 × 3 (+ 포함)",
             note=["수신기·MUX 모두 UBEC B → 3선 그대로", "MUX 전원(VM·VS)도 이 선으로 들어감",
                   "CH5는 2단 스위치에 배정 (송신기 Aux. channels)"]),
        dict(src="신호 MUX", src_sub="Pololu 2806 출력", dst="MDDS30", dst_sub="RC 입력 헤더",
             pins=[("OUT1 신호", "s", "RC1 신호 (조향)", "s"), ("OUT1 GND", "g", "RC1 GND", "g"),
                   ("OUT2 신호", "s", "RC2 신호 (구동)", "s"), ("OUT2 GND", "g", "RC2 GND", "g"),
                   ("(빨간 선)", "n", "RC 가운데 5 V", "p")],
             cable="신호·GND만 — 빨간 선 빼기",
             note=["MDDS30 RC 가운데는 드라이버 자체 5 V", "이으면 UBEC B와 드라이버 5 V가 맞붙음"]),
        dict(src="릴레이 접점", src_sub="K1–K4 (각 30·87a·87)", dst="모터 선", dst_sub="authority tap (§3.4 표)",
             pins=[("30 (COM)", "m", "모터 쪽 (K1·K2 조향, K3·K4 구동)", "m"),
                   ("87a (NC)", "m", "순정 ECU 쪽 = STOCK", "m"), ("87 (NO)", "m", "MDDS30 MLA·MLB·MRA·MRB = DBW", "m")],
             cable="모터 전류 선 (전원 팀)",
             note=["한 쌍의 87a·87을 바꾸면 DBW만 반대로 돈다", "→ 선을 고친다 (펌웨어 부호 X)"]),
        dict(src="스타 접지", src_sub="모터 드라이버(MDDS30) 한 점", dst="모이는 GND", dst_sub="신호 GND",
             pins=[("●", "g", "신호 기판 (Teensy)", "g"), ("●", "g", "수신기", "g"), ("●", "g", "신호 MUX", "g"),
                   ("●", "g", "릴레이 구동 기판", "g"), ("●", "g", "MDDS30 (팩 −)", "g")],
             cable="한 점에서만 묶기",
             note=["여러 경로로 이으면 접지 고리 (FMEA row 5)", "→ 모터가 엉뚱하게 움직이는데 펌웨어 버그처럼 보임"]),
        dict(src="노트북", src_sub="ROS 2 + micro-ROS agent", dst="Teensy 4.1", dst_sub="신호 기판 소켓",
             pins=[("USB", "s", "USB (데이터)", "s")],
             cable="USB 케이블",
             note=["VUSB–VIN 절단 후에는 데이터만", "전원은 PWR 단자(UBEC A)로"]),
    ]),
]

W = 1400
PIN_H = 24
SX0, SX1 = 30, 270          # source box
DX0, DX1 = 700, 990          # destination box
NX = 1010                    # notes
o = []


def a(s):
    o.append(s)


def txt(x, y, s, size=13, fill="#0f172a", weight="normal", anchor="start"):
    a(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{s}</text>')


a("<svg>")
a("<rect/>")
txt(30, 38, "MRider 전체 배선 연결도 — 단자·핀마다 어디로 가는가", 21, weight="bold")
txt(30, 62, "출처: 03-electrical.md (전원 구조, §3.4 E-stop·릴레이, §3.5.1 수신기·MUX, §3.5.2 센서 케이블, §3.5.4 신호 기판), "
    "sensors.md §3 (IMU), dbw.md §4.1 (MDDS30), 팀 배치도 (신호 기판 IMU판, 릴레이 구동 기판)", 12, "#475569")
txt(30, 80, "선 색: 빨강 = 전원, 회색 = GND, 파랑 = 신호, 주황 = 모터 전류, 점선 = 일부러 연결하지 않음. 핀 위치·좌표는 각 기판 배치도를 본다.", 12, "#475569")

y = 104
for title, tcol, rows in SECTIONS:
    a(f'<rect x="20" y="{y}" width="{W-40}" height="34" rx="6" fill="{tcol}" opacity="0.12"/>')
    txt(34, y + 23, title, 16, tcol, "bold")
    y += 48
    for row in rows:
        n = len(row["pins"])
        h = max(n * PIN_H + 36, 22 * len(row["note"]) + 36)
        top = y
        py0 = top + 34
        # boxes
        a(f'<rect x="{SX0}" y="{top}" width="{SX1-SX0}" height="{n*PIN_H+40}" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.8"/>')
        a(f'<rect x="{DX0}" y="{top}" width="{DX1-DX0}" height="{n*PIN_H+40}" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.8"/>')
        txt(SX0 + 10, top + 18, row["src"], 13.5, weight="bold")
        txt(SX1 - 10, top + 18, row["src_sub"], 11, "#64748b", anchor="end")
        txt(DX0 + 10, top + 18, row["dst"], 13.5, weight="bold")
        txt(DX1 - 10, top + 18, row["dst_sub"], 11, "#64748b", anchor="end")
        for k, (sp, sk, dp, dk) in enumerate(row["pins"]):
            yy = py0 + k * PIN_H + 6
            kind = "n" if "n" in (sk, dk) else ("p" if "p" in (sk, dk) and "g" not in (sk, dk) else sk)
            col = COL[kind]
            txt(SX1 - 14, yy + 4, sp, 12.5, COL[sk], "bold", "end")
            txt(DX0 + 14, yy + 4, dp, 12.5, COL[dk], "bold")
            a(f'<circle cx="{SX1}" cy="{yy}" r="4.5" fill="{COL[sk]}"/>')
            a(f'<circle cx="{DX0}" cy="{yy}" r="4.5" fill="{COL[dk]}"/>')
            if kind == "n":
                a(f'<line x1="{SX1+6}" y1="{yy}" x2="{DX0-6}" y2="{yy}" stroke="{col}" stroke-width="2" stroke-dasharray="6 5"/>')
                mx = (SX1 + DX0) / 2
                a(f'<path d="M{mx-7} {yy-7} L{mx+7} {yy+7} M{mx-7} {yy+7} L{mx+7} {yy-7}" stroke="#dc2626" stroke-width="2.4"/>')
            else:
                a(f'<line x1="{SX1+6}" y1="{yy}" x2="{DX0-6}" y2="{yy}" stroke="{col}" stroke-width="2.6"/>')
        # cable label above the bundle
        cx = (SX1 + DX0) / 2
        a(f'<rect x="{cx-150}" y="{top+2}" width="300" height="22" rx="11" fill="#f1f5f9" stroke="#cbd5e1"/>')
        txt(cx, top + 18, row["cable"], 11.5, "#334155", "bold", "middle")
        for k, ln in enumerate(row["note"]):
            txt(NX, top + 20 + k * 20, ln, 12, "#334155")
        y = top + max(n * PIN_H + 40, h) + 14
    y += 10

H = y + 10
o[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        "font-family=\"'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif\">")
o[1] = f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
a("</svg>")

def table():
    """The same ROWS as a markdown table per section, for the guide (python3 ... --table)."""
    out = []
    for title, _, rows in SECTIONS:
        out += [f"#### {title}", "", "| 출발 | 도착 | 핀 대응 (출발 → 도착) | 선 |", "|---|---|---|---|"]
        for r in rows:
            pairs = []
            for sp, sk, dp, dk in r["pins"]:
                pairs.append(f"{sp} ✕ {dp} (잇지 않음)" if "n" in (sk, dk) else f"{sp} → {dp}")
            out.append(f"| **{r['src']}** ({r['src_sub']}) | **{r['dst']}** ({r['dst_sub']}) | "
                       f"{'<br>'.join(pairs)} | {r['cable']} |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    if "--table" in sys.argv:
        print(table())
        sys.exit()
    dst = HERE / "system_wiring.svg"
    dst.write_text("\n".join(o), encoding="utf-8")
    n = sum(len(r["pins"]) for _, _, rows in SECTIONS for r in rows)
    print(f"wrote {dst.relative_to(ROOT)}  ({sum(len(rows) for _, _, rows in SECTIONS)} connectors, {n} pins, canvas {W}x{H})")

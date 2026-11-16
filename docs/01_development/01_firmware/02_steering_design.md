# 조향 펌웨어 설계 — `firmware/steering`

`mitt_dbw` 펌웨어에 추가할 **조향 기능**의 설계 문서다. 무엇을 만들지, 그 근거가 문서의 어디에 있는지,
문서에 없어서 팀이 정해야 하는 것은 무엇인지를 정리한다.

- **상태:** 설계 (구현 전). 결정이 필요한 항목은 5장에 따로 모았다.
- **대상 독자:** Track E 팀원, 조향 기능 구현·튜닝을 맡을 사람
- **전제:** Stage 0 센싱 펌웨어(`firmware/sensing`) 위에 쌓는다. 구조는 `01_firmware_development.md` 5장을 본다.
- **원본 문서:** `docs/design/dbw.md` §3·§10·§12, `docs/design/safety.md` §1·§2·§6, `docs/build/04-firmware.md` §4.4·§4.5,
  `docs/build/03-electrical.md` §3.5, `docs/learn/m2-dbw-steering.md` Part 3, `docs/design/calibration.md` §1, `docs/order-log.md` (RC 채널)
- **표기:** 근거가 문서에 있으면 출처를 적는다. 문서에 없어서 정한 것은 **[결정 Dn]**, 숫자는 `mitt_config.h` 태그(`[POLICY]`·`[TUNE]`·`[MEASURE]`)로 표시한다.

---

## 1. 목표

| | 1차 목표 | 2차 목표 |
|---|---|---|
| **무엇** | **RC 송신기로 조향** | **컴퓨터가 보낸 값으로 조향** |
| 경로 | 송신기 → 수신기(i-BUS) → Teensy → 위치 루프 → MDDS30 → 조향 모터 | 노트북 `/mitt/dbw/command` → Teensy → 위치 루프 → MDDS30 → 조향 모터 |
| 모드 | `MANUAL_RC` | `AUTONOMOUS` |
| 문서상 위치 | Stage 2 **Layer A** (`04-firmware.md` §4.5) | Stage 1 (`04-firmware.md` §4.4) = **Merge 1(11/23)** 의 주장 |

- **왜 RC가 먼저인가**
  - 문서는 ESTOP에서 나오는 유일한 길을 "E-stop 해제 + **RC arm**"으로 정했다(`dbw.md` §10.3). RC가 먼저 있어야 문서 방식대로 출발을 허가할 수 있다.
  - "사람이 언제든 차를 되찾을 수 있다"는 조건(Track E 목표, `docs/course/teams.md`)이 컴퓨터 제어보다 먼저 갖춰진다.
- **"RC로 조향"의 뜻:** Teensy가 i-BUS를 읽어 **스틱을 조향각으로 바꾸고, 위치 루프를 닫은 채로** 따라가게 한다(**Layer A**, `safety.md` §1.2).
  - 수신기를 드라이버에 직접 잇는 **Layer B**(신호 MUX)는 펌웨어가 아니라 배선의 성질이다. Teensy를 멈춘 상태에서 따로 시험한다(`04-firmware.md` §4.5).
- **두 목표 모두 위치 루프가 필요하다.** 1차 목표에서는 스틱으로 조향할 수 있을 만큼 기본 튜닝을 한다. 2차 목표에서 컴퓨터 명령으로 정밀 튜닝과 6가지 측정을 한다.
- **제외 (다음 단계):**
  - 구동 채널: 핀 3은 계속 1500 µs이고, 스로틀(CH2)은 읽기만 하고 무시한다.
  - E-stop 감지 입력, 릴레이: 핀 20은 읽지 않고, 핀 21은 계속 LOW(STOCK)다.
  - 이 둘은 전원 팀 회로와 함께 `firmware/estop`에서 추가한다.

---

## 2. 요구사항과 근거

### 2.1 공통 — 위치 루프

| ID | 요구사항 | 출처 |
|---|---|---|
| P1 | 위치 PID를 **≥ 200 Hz**로 돌린다. 오차 = 목표 − 측정, 출력 = 부호 있는 effort | `dbw.md` §10.2 ③, §12 |
| P2 | 서보 PWM → 신호 MUX → MDDS30 RC1. 정지는 정확히 1500 µs | `dbw.md` §10.2 ④, §12 |
| P3 | PWM 주기는 **측정해서 고정**한다 | `dbw.md` §12, `04-firmware.md` §4.4 |
| P4 | 목표각은 ±22.5°(±0.3927 rad)로 제한한다 | `dbw.md` §10.1, §12 |
| P5 | PID 게인 같은 설정은 **ROS 2 파라미터·서비스**로 다룬다 | `dbw.md` §10.1 |
| P6 | **한계 클램프:** 끝 근처에서는 중앙 쪽 effort만 허용하고 `FAULT_AT_LIMIT`를 켠다 | `dbw.md` §10.2 ⑦, `safety.md` row 7 |
| P7 | **stall 감지:** `FAULT_STALL`을 켜고 effort를 줄인다 | `dbw.md` §10.2 ⑦, `safety.md` row 7 |
| P8 | **나쁜 각도로는 루프를 돌리지 않는다** (센서 고장 → ESTOP, 출력 중립) | `safety.md` row 9 |
| P9 | ESTOP으로 들어갈 때는 throttle 0, **조향은 중앙 복귀 후 정지** | `dbw.md` §10.3 |
| P10 | 워치독은 완료된 루프만 먹인다. **hang 테스트 빌드**로 확인한다 | `safety.md` row 8, `04-firmware.md` §4.4 |
| P11 | 루프를 닫기 전에 **출력 부호를 개루프로** 확인한다 | `m2-dbw-steering.md` Part 3 |
| P12 | 튜닝 순서는 P → D → I. I는 마지막에 조금만 쓰고 **누적을 제한**한다 | `04-firmware.md` §4.4, `m2-dbw-steering.md` Part 3 |
| P13 | 신호 끊김 정지(`SW6 = 0`)는 **펄스를 멈춰서** 확인한다 | `04-firmware.md` §4.4 |

### 2.2 1차 목표 — RC (Layer A)

| ID | 요구사항 | 출처 |
|---|---|---|
| A1 | i-BUS를 **하드웨어 시리얼** Serial3 RX(**핀 15**)로 받는다. 115200 8N1, **반전 없음** | `04-firmware.md` 핀 표·§4.5 |
| A2 | 수신기는 5 V로 동작하고 Teensy는 5 V를 견디지 못한다. **i-BUS 대기 전압을 먼저 재고**, 그 결과로 R5·R6(점퍼 또는 분압)을 정한다 | `03-electrical.md` §3.5.4, `04-firmware.md` §4.3 |
| A3 | 채널: **CH1 = 조향(오른쪽 스틱 좌우)**, CH2 = 스로틀(오른쪽 스틱 상하), **CH5 또는 CH6 = 신호 MUX SEL**(2단 스위치) | `order-log.md` 267–269행 |
| A4 | 모드 스위치로 `MANUAL_RC`에 들어간다. **스틱은 각도를 명령**하고, 위치 루프는 닫힌 상태를 유지한다 | `04-firmware.md` §4.5, `safety.md` §1.2 |
| A5 | ESTOP에서 나오는 길은 **RC arm**뿐이다 | `dbw.md` §10.3 |
| A6 | **RC override는 어느 상태에서든 200 ms 이내**에 걸린다 | `dbw.md` §10.3, §12 |
| A7 | **RC 프레임 끊김 → ESTOP**: throttle 0, 조향은 중앙 복귀 후 정지. 다시 연결돼도 **명시적으로 재허가**해야 움직인다 | `04-firmware.md` §4.5, `safety.md` §2 row 3 |
| A8 | `MANUAL_RC` 상태는 `DbwStatus.mode`(1)로 보이고, RC 끊김은 `FAULT_RC_LOSS`(16)로 보인다 | `04-firmware.md` §4.5, `DbwStatus.msg` |

### 2.3 2차 목표 — 컴퓨터 명령

| ID | 요구사항 | 출처 |
|---|---|---|
| C1 | `/mitt/dbw/command`(`DbwCommand.steering_angle`, rad)를 받는다. 노트북은 **≥ 50 Hz**로 보낸다 | `dbw.md` §10.1, §12 |
| C2 | `MANUAL_RC` → `AUTONOMOUS`는 **RC 모드 스위치**로 바꾼다 | `dbw.md` §10.3 상태도 |
| C3 | `AUTONOMOUS`는 **명령이 살아 있어야** 유지된다. 500 ms 넘게 끊기면 ESTOP으로 간다 | `dbw.md` §10.3, §12, `safety.md` row 1 |
| C4 | `AUTONOMOUS` 중에도 RC override가 200 ms 이내에 걸린다 | `dbw.md` §10.3 |
| C5 | 스텝 응답은 `/mitt/dbw/status`의 `steering_setpoint`와 `steering_angle`을 **≥ 200 Hz**로 기록해 비교한다 | `04-firmware.md` §4.4, `m2-dbw-steering.md` Part 3 |
| C6 | 통과 수치: 정상상태 ≤ 1.0°, 스윕 RMS ≤ 1.5°, 10° 스텝 90% 도달 ≤ 400 ms·오버슈트 ≤ 15%, 30분 드리프트 ≤ 0.5°. 못 맞추면 **E4** 결정 | `dbw.md` §3·§12, `04-firmware.md` §4.4 |

---

## 3. 상태와 전이

```
            RC arm (모드 스위치 KILL→MANUAL, 스틱 중앙) [D1]
   ┌───────┐ ───────────────────────────────────────────▶ ┌───────────┐
   │ ESTOP │                                               │ MANUAL_RC │ ◀── 스틱 = 조향각
   └───────┘ ◀─────────────────────────────────────────── └───────────┘
       ▲      RC 끊김 / KILL / 센서 고장 / Layer B [D5]       │     ▲
       │                                          모드 AUTO   │     │ 모드 MANUAL 또는
       │                                        + 명령 수신중 ▼     │ 스틱을 크게 움직임 (override)
       │      RC 끊김 / KILL / 센서 고장 / 명령 500 ms 끊김  ┌────────────┐
       └──────────────────────────────────────────────────── │ AUTONOMOUS │ ◀── 노트북 명령 = 조향각
                                                             └────────────┘
```

| 전이 | 조건 | 근거 |
|---|---|---|
| ESTOP → MANUAL_RC | 모드 스위치를 KILL에서 MANUAL로 **올리는 순간**, 스틱 중앙, RC 정상, 센서 정상 | A5, **[D1]** |
| MANUAL_RC → AUTONOMOUS | 모드 스위치를 MANUAL에서 AUTO로 **올리는 순간**, 명령 수신 중 | C2 |
| AUTONOMOUS → MANUAL_RC | 모드 스위치 MANUAL, 또는 스틱을 크게 움직임(override) | A6, C4, **[D1]** |
| 모든 상태 → ESTOP | RC 끊김, 모드 스위치 KILL, 센서 고장 | A7, P8 |
| AUTONOMOUS → ESTOP | 명령 500 ms 끊김 | C3 |

- **ESTOP으로 들어갈 때의 동작**
  - 센서가 정상이면 **중앙 복귀 후 정지**한다(P9). 0°로 PID를 돌리고, 1° 이내에서 150 ms 머물면 정지한다. 1.5초 안에 못 가면 그냥 정지한다 `[POLICY]`.
  - 센서 고장이면 **즉시 1500 µs**로 정지한다. 엉터리 각도를 향해 움직이지 않는다(P8).
- **다시 움직이려면** 반드시 RC arm을 새로 해야 한다(A7). 연결이 돌아왔다는 것만으로는 출발하지 않는다.
- **E-stop 감지가 들어오면**(`firmware/estop`) 문서의 전체 조건 "E-stop 해제 + RC arm"을 완성한다. 지금 단계에서도 **하드웨어 E-stop은 펌웨어와 관계없이 전원을 끊는다.**

---

## 4. 설계

### 4.1 구조

Stage 0 구조를 그대로 두고, 판단 코드와 입출력을 더한다.

| 파일 | 하는 일 | 상태 |
|---|---|---|
| `src/sensors.*` | 각도 신뢰 판단(`AngleCheck`) — P8 | **재사용** |
| `src/calibration.*` | θ = k·(raw − c0), c0 EEPROM | 재사용 |
| `src/ibus.*` | **새로 추가.** i-BUS 프레임 해석(32바이트, 체크섬). Arduino 무의존 → PC 테스트 — A1 | 신규 |
| `src/steer_core.*` | **새로 추가.** 상태 전이(3장), RC 해석(스위치·스틱), PID, 안전 규칙. Arduino 무의존 → PC 테스트 | 신규 |
| `src/hal.*` | Serial3 i-BUS 수신, `WriteSteerEffort()`(effort → 펄스 → 핀 2) | 확장 |
| `src/uros_node.*` | 명령 구독(C1), 파라미터 서버(P5), 상태 200 Hz(C5) | 확장 |
| `src/main.cpp` | 루프: 읽기(센서·RC·명령) → 판단 → 쓰기 → 워치독 | 확장 |
| `test/host/` | `test_ibus.cpp`, `test_steer.cpp` | 신규 |
| `firmware/bench/src/ibus_monitor.cpp` | 수신기 프레임·채널 배치·RC 끊김 확인 — A1~A3, A7 | 이 단계에서 커밋 |
| `firmware/bench/src/pwm_effort_check.cpp` | 개루프 부호·PWM 주기·신호 끊김·hang — P3, P11, P13 | 이 단계에서 커밋 |

### 4.2 RC 입력 해석

- **프레임:** i-BUS는 약 7.7 ms마다 32바이트 프레임(14채널, 각 1000~2000 µs)을 보낸다. 체크섬이 맞는 프레임만 쓴다.
- **RC 정상 판단:** 새 프레임이 100 ms 넘게 안 오면 끊김으로 본다 `[POLICY]`. 사용하는 채널 값이 900~2100 µs를 벗어나도 비정상으로 본다.
- **송신기 failsafe:** FS-iA6B는 송신기가 꺼져도 **failsafe 값으로 프레임을 계속 보낼 수 있다.** 이 경우 프레임 끊김만으로는 RC 상실을 알 수 없으므로, **송신기에서 모드 채널의 failsafe를 KILL로 설정**한다(**[D2]**, `ibus_monitor`로 확인).
- **조향 스틱(CH1):** 1500 µs를 중앙으로 ±500 µs를 −1~+1로 바꾸고, 중앙 5%는 데드밴드로 0 처리한다 `[POLICY]`.
  - 결과에 `kRcSteerSign · 22.5°`를 곱해 목표각으로 쓴다. 스틱을 오른쪽으로 밀면 어느 쪽 각도가 되는지는 `[MEASURE]`이며, 왼쪽이 +다(`calibration.md` §1).
- **모드 스위치:** 3단 스위치 KILL / MANUAL / AUTO (**[D1]**)
- **신호 MUX SEL:** 수신기가 드라이버에 직접 연결된 상태(Layer B)를 Teensy가 알 수 있다. 처리 방법은 **[D5]**.

### 4.3 위치 루프

- **오차:** `e = 목표 − 측정` (rad). 목표는 ±(22.5° − 0.5°)로 제한해서 한계 클램프와 겹치지 않게 한다.
- **P:** `kp · e`
- **D:** `−kd · (측정 각속도)`
  - 측정값의 미분을 쓰므로 목표가 갑자기 바뀌어도 튀지 않는다.
  - 각속도에는 20 Hz 저역통과 필터를 건다 `[TUNE]`.
- **I:** `ki · ∫e dt`
  - 출력이 이미 한계에 붙어 있으면 더 쌓지 않는다.
  - 누적값은 ±0.2 effort로 제한한다(P12, `[TUNE]`).
- **출력:** `effort = clamp(P + I + D, ±effort_max)`
- **펄스:** `1500 + kSteerEffortSign · effort · 500 µs`
  - effort 0이면 정확히 1500 µs다.
  - 부호(`kSteerEffortSign`)는 P11 확인 결과로 정한다 `[MEASURE]`.
- **PWM 주기:** 50 Hz로 시작한다 `[MEASURE]`. 측정 후 고정한다(P3). 핀 2·3은 같은 타이머라 함께 바뀐다.
- **게인:** ROS 2 파라미터 `kp` `ki` `kd` `effort_max`로 실행 중 바꾼다(P5).
  - 음수, NaN, `effort_max`가 0 이하이거나 1 초과면 거부한다.
  - 재부팅하면 `mitt_config.h` 기본값으로 돌아가므로, 튜닝이 끝나면 기본값에 옮겨 적는다.

### 4.4 안전 규칙 (매 주기 이 순서로)

1. **센서(P8):** `AngleCheck`가 믿을 수 없다고 하면 ESTOP + 1500 µs.
2. **RC(A7):** RC 끊김, 모드 KILL, Layer B([D5])이면 ESTOP + 중앙 복귀.
3. **명령(C3):** AUTONOMOUS에서 명령이 500 ms 끊기면 ESTOP + 중앙 복귀.
   - 명령 순번이 바뀔 때만 새 명령으로 본다. 그래서 `micros()`가 한 바퀴 돌아도 오래된 명령이 새것처럼 보이지 않는다.
4. **한계 클램프(P6):** |각도| ≥ 22.0°이면 바깥쪽 effort를 0으로 막고 `FAULT_AT_LIMIT`를 켠다.
5. **stall(P7):** |effort| ≥ 0.25이고 각속도 < 2°/s이고 오차 > 2°인 상태가 0.5초 이어지면 `FAULT_STALL`을 켜고 effort를 ±0.15로 줄인다 `[POLICY]`.

### 4.5 인터페이스

| 이름 | 방향 | 내용 | 근거 |
|---|---|---|---|
| i-BUS (핀 15) | 수신기 → Teensy | CH1 조향, CH2 스로틀(무시), MUX SEL, 모드 | A1, A3 |
| `/mitt/dbw/command` | 노트북 → Teensy | `steering_angle` 사용. `speed`는 무시(구동은 다음 단계) | C1 |
| `/mitt/dbw/status` | Teensy → 노트북, **200 Hz** | `mode`(0·1·2), `steering_setpoint`, `steering_angle`, `faults`(1·2·4·8·16) | A8, C5 |
| 파라미터 `kp` `ki` `kd` `effort_max` | 양방향 | 실행 중 게인 변경 | P5 |
| `/mitt/dbw/zero_steering` | 노트북 → Teensy | 영점 저장. **ESTOP이고 중앙 복귀 중이 아닐 때만** | Stage 0 + P9 |
| `/mitt/dbw/debug` | Teensy → 노트북 | effort, P·I·D 항, 각속도, raw, 펄스 폭, RC 채널 값 | **[D4]** |
| `/mitt/dbw/hang_test` (hang 빌드만) | 노트북 → Teensy | 받으면 루프 안에서 멈춤 | P10, **[D6]** |

### 4.6 micro-ROS 자원과 타이밍

- **서비스 6개:** 파라미터 서버 5개 + 영점 1개. 라이브러리는 `RMW_UXRCE_MAX_SERVICES=6`으로 이미 빌드했다(`microros/colcon.meta`). 컴파일 때 검사하도록 `static_assert`를 넣는다.
- **노트북 연결과 RC 조향은 독립적이다.** `MANUAL_RC`는 agent가 없어도 동작해야 한다. RC 조향이 USB 연결에 의존하면 안 된다.
- **연결 과정이 길어질 수 있다.** 파라미터 서버는 서비스를 한 번에 5개 만들기 때문에, agent가 느리면 연결 과정이 워치독(250 ms)에 가까워질 수 있다. 그래서 30분 안정성 시험에 **agent 재시작**을 포함한다.

### 4.7 hang 테스트 빌드

- `pio run -e mitt_dbw_hangtest`로 만든다. `/mitt/dbw/hang_test`를 받으면 제어 루프 안에서 멈춘다.
- **기대 동작:** 워치독 리셋(250 ms) → 펄스가 끊김 → MDDS30 신호 끊김 정지(100 ms). 따라서 **약 350 ms 안에 모터가 멈춰야** 한다.

---

## 5. 문서에 없는 결정 (팀 확인 필요)

| ID | 항목 | 문제 | 선택지 | 추천 | 상태 |
|---|---|---|---|---|---|
| **D1** | **모드 스위치 채널과 arm 동작** | 문서는 "RC arm"과 "RC mode switch"를 요구하지만 **채널과 동작은 정하지 않았다.** MUX SEL이 CH5 또는 CH6이니 남은 하나를 써야 한다 | (a) 3단 스위치(SwC) 하나에 KILL/MANUAL/AUTO, KILL→MANUAL로 올릴 때 arm (b) arm과 모드를 2단 스위치 두 개로 나눔 | (a) — FS-i6 기본 6채널 안에서 해결된다. 스틱 중앙 조건을 붙여 갑자기 꺾이는 것을 막는다 | 결정 대기 |
| **D2** | 송신기 failsafe | FS-iA6B는 송신기가 꺼져도 failsafe 값으로 프레임을 계속 보낼 수 있다 | 모드 채널 failsafe = KILL로 송신기 설정 | 설정하고 `ibus_monitor`로 확인 | 결정 대기 |
| **D3** | 수치 기준값 | RC 끊김 100 ms, 데드밴드 5%, override 기준(스틱 30%), stall(0.25·2°/s·2°·0.5 s·0.15), 중앙 복귀(1°·150 ms·1.5 s), 한계 여유 0.5°, effort 시작값 0.6 | — | `[POLICY]`/`[TUNE]`로 두고 측정해 확정, 기록 | 결정 대기 |
| **D4** | debug 토픽 | 튜닝에는 effort·P·I·D가 필요하다. 그런데 문서는 진단을 "파라미터·서비스로, **별도 채널 없이**" 하라고 한다(`dbw.md` §10.1) | (a) 튜닝 동안 유지하고 이후 빌드 옵션으로 끔 (b) 빼고 status만으로 튜닝 (c) `DbwStatus`에 필드 추가 | (a) — 인터페이스 계약은 건드리지 않고 이유를 기록 | 결정 대기 |
| **D5** | Layer B 선택 시 처리 | MUX가 수신기를 드라이버에 직접 연결하면 Teensy 펄스는 모터에 닿지 않는다. 이때 Teensy가 계속 루프를 돌리면 적분이 쌓이고, Layer A로 돌아오는 순간 튈 수 있다 | (a) ESTOP으로 가고 재허가 필요 (b) 루프만 멈추고 상태 유지 | (a) — 돌아올 때 의도적으로 허가하게. 상태를 알리는 고장 비트는 `DbwStatus.msg`에 없음 → 메시지에 추가할지 함께 결정 | 결정 대기 |
| **D6** | hang 신호 경로 | 문서는 "시리얼 명령으로"라고 하지만 시리얼은 micro-ROS가 쓴다 | ROS 토픽 | 토픽 (루프 안에서 멈추는 동작은 문서와 같다) | 결정 대기 |
| **D7** | E-stop 감지 없이 진행 | 문서의 ESTOP 탈출 조건은 "E-stop 해제 + RC arm"인데, 감지 회로는 전원 팀 작업이다 | (a) 이 단계는 RC arm만, E-stop 감지는 `firmware/estop`에서 추가 (b) 감지 회로가 올 때까지 대기 | (a) — 하드웨어 E-stop은 펌웨어와 관계없이 동작한다. 감지는 재출발 방지용(`safety.md` §1) | 결정 대기 |

- 결정되면 이 표의 상태를 바꾸고, 결정 이유를 `01_firmware_development.md` 개발 과정에 기록한다.

---

## 6. 하드웨어 전제와 배선

- **회로도**
  - 벤치: `docs/02_guide/01_firmware/images/steer_bench_schematic.svg` (Teensy 실제 핀 배치 기준, 생성 스크립트 동봉)
  - 신호 보드(PCB) 구멍 단위 배치: `docs/images/signal-board-perfboard-layout.svg` — `PWM 1 · steer` 헤더, `i-BUS in` 단자와 R5·R6
  - 수신기·MUX·드라이버·E-stop 관계: `docs/images/rc-mux-estop.svg`
  - 저항·커패시터 이름(R1·R2 = SCL·SDA 4.7 kΩ, R3·R4 = 엔코더 10 kΩ, C1·C2 = 1 nF)은 공식 PCB 그림을 따른다.
- **신호 MUX 실물 핀 배치 (Pololu `rcm01b`, 2026-11-14 보드 확인)**
  - `SEL`·`M1~M4`·`OUT1~OUT4`는 가운데 핀이 **VM**, `S1~S4`는 가운데 핀이 **VS**로 서로 다른 전원선이다.
    문서의 "SEL·MASTER·OUT은 VM 하나"(`03-electrical.md` §3.5.1)와 일치한다.
  - 앞면(부품면)에서 보면 두 블록 모두 **신호 핀이 보드 안쪽, GND가 바깥 가장자리**다.
  - 연결:
    - 수신기 CH5 → `SEL`(3선, VM 전원도 여기서), 수신기 CH1 → `S1`(3선, VS 전원도 여기서)
    - Teensy 핀 2 → `M1`(신호·GND만), `OUT1` → MDDS30 RC1(신호·GND만)
    - `FAILMODE`에는 점퍼를 꽂지 않는다.
  - 앞면 배선 그림은 벤치 회로도 아래쪽 패널에 있다.

### 6.1 공통

- **AS5600이 조향축(킹핀, load-side)에 장착돼 있어야 한다.** 센서 마운트는 출력 중이다.
- **Stage 0 마무리가 먼저다:** wrap 검사와 k·c0 보정(`calibration.md` §1)을 마쳐야 한다.
- **조향 모터:** 차량 조향 장치에 연결한 상태로, 바퀴는 띄운다.
- **MDDS30:** 모터 Left → 조향 모터.
  - DIP 스위치: `SW1·2 = 0 0`, `SW3·4 = 1 1`, `SW5 = 0`, `SW6 = 0`, `SW7·8 = 1 0` (`03-electrical.md` §3.5)
- **실험용 전원(전류 제한):** 모터가 무부하로 겨우 돌 정도로 제한한다(`04-firmware.md` §4.4).
- **신호:** 핀 2 → 신호 MUX master → MDDS30 RC1.
  - 서보 케이블의 +5 V선은 연결하지 않는다(`03-electrical.md` §3.5.1).
  - MUX의 FAILMODE 점퍼 방향은 아직 결정되지 않았다(`dbw.md` §13).
- **켜는 순서:** Teensy → MUX → MDDS30. 드라이버는 켜질 때 보는 펄스를 정지로 학습한다.
- **접지:** 모든 신호 GND를 드라이버의 한 점에 모은다.

### 6.2 1차 목표에 추가로 필요한 것

- **송신기 FS-i6 + 수신기 FS-iA6B:** 3세트 구매 완료(`order-log.md` 10행)
- **수신기 전원 5 V:** 차량에서는 UBEC B를 쓴다(전원 팀). 벤치에서는 별도 5 V를 쓰고, GND는 공통으로 묶는다.
- **i-BUS → 핀 15:** **먼저 대기 전압을 잰다.** 3.3 V면 그대로, 5 V면 분압 저항을 넣는다(R5·R6).
  - **측정 완료(2026-11-14): 3.3 V → R5 점퍼선, R6 생략.** SERVO 포트 위 핀 = 신호, 가운데 = +5 V.
    결과는 [조향 벤치 검증](../../03_validation/01_firmware/02_steering_bench.md) §1.
  - 연결할 때는 **신호와 GND만** Teensy 쪽으로 보낸다. 가운데 +5 V는 Teensy에 연결하지 않는다.
- **신호 MUX SEL ← CH5 또는 CH6, MUX slave ← 수신기 CH1·CH2:** Layer B 배선이다(`03-electrical.md` §3.5.1).

---

## 7. 검증 계획

결과는 `docs/03_validation/01_firmware/`에 기록한다(측정값, 날짜, 펌웨어 커밋 해시).

### 7.1 1차 목표 — RC 조향

1. **출력 부호(P11):** `pwm_effort_check`로 +effort를 줬을 때 각도가 커지는지 확인하고 `kSteerEffortSign`을 정한다.
2. **PWM 주기·신호 끊김(P3·P13):** 50 → 100 → 200 → 300 Hz를 시험한다. 펄스를 멈추면 100 ms 안에 정지하는지 확인한다.
3. **수신기 확인(A1~A3, D2):** `ibus_monitor`로 아래를 확인한다.
   - 프레임이 초당 약 130개 들어오는지
   - 체크섬 오류가 없는지
   - 채널 배치가 맞는지
   - 송신기를 끄면 `NO FRAMES`가 뜨는지, 또는 failsafe로 모드 채널이 KILL이 되는지
4. **PC 테스트:** i-BUS 해석, 상태 전이, 안전 규칙. 규칙을 지운 변형 코드가 테스트에 잡히는지도 본다.
5. **기본 튜닝(P12):** P부터 시작해 스틱으로 조향할 때 진동 없이 따라가는 수준까지 맞춘다.
6. **RC 동작 확인**
   - KILL → MANUAL로 올리면 `mode 1`이 되는가
   - 스틱이 **각도**를 명령하는가: 손을 떼면 중앙으로 돌아오는가
   - 송신기를 끄면 ESTOP이 되고 중앙 복귀 후 정지하는가
   - 다시 켜도 재허가 전에는 움직이지 않는가
7. **안전 동작:** 한계 클램프, stall, 센서 선을 뽑았을 때 즉시 정지
8. **hang 테스트(P10):** 약 350 ms 안에 멈추는지 확인한다.
9. **Layer B (배선 검증):** Teensy를 멈춘 상태에서 MUX를 전환해 송신기로 직접 조향되는지 확인한다(`04-firmware.md` §4.5).

### 7.2 2차 목표 — 컴퓨터 조향 (Merge 1)

1. MANUAL → AUTO로 올리면 `mode 2`가 되고 명령 각도를 따라가는지 확인한다.
2. 명령을 끊으면 500 ms 안에 ESTOP이 되고 중앙 복귀 후 정지하는지 확인한다.
3. AUTONOMOUS 중 스틱을 움직이거나 MANUAL로 내리면 200 ms 안에 사람에게 넘어오는지 확인한다.
4. **정밀 튜닝과 6가지 측정(C6):** 정상상태 오차, 스윕 RMS, 10° 스텝, 백래시, 30분 드리프트, 외란 복귀
5. **E4 결정:** 결과가 어느 쪽이든 기록한다.

---

## 8. 구현 계획

- **브랜치:** `firmware/steering`. `firmware/sensing`이 `main`에 합쳐졌으면 `main`에서, 아직이면 `firmware/sensing`에서 만든다.
- **재사용할 코드**
  - 앞서 작성하고 테스트한 PID·안전 규칙·파라미터 코드: 저장소 밖 `../mrider-wip/`
  - 이전 전체 버전의 i-BUS 해석과 RC 상태 전이: 루트의 `mitt_dbw_firmware.patch` 안 `ibus.*`, `dbw_core.*`
  - 둘 다 이 설계(특히 5장 결정)에 맞춰 다시 정리하고, 구동·E-stop·릴레이 부분은 뺀다.
- **커밋 순서 (예정)**
  1. 이 설계 문서
  2. `ibus` + 단위 테스트, `ibus_monitor` 스케치
  3. `steer_core`(상태 전이·PID·안전 규칙) + 단위 테스트
  4. `hal`·`uros_node`·`main` 확장, 파라미터 서버, hang 빌드, `pwm_effort_check`
  5. 회로도 갱신(핀 2·15 사용, 수신기·MUX·MDDS30 추가), 가이드 7.4·7.5 확인
  6. 1차 목표 검증 결과 → 2차 목표 검증 결과
- **문서 갱신:** 개발 기록(구조와 결정), 가이드(사용법), 검증 문서(결과)

# 펌웨어 개발 문서 — `firmware/mitt_dbw`

MRider DBW 펌웨어(Teensy 4.1)의 **현재 구조, 개발 환경, 개발 과정과 결정 이유**를 기록한다.
팀원이 이 문서만 읽고도 "지금 무엇이 있고, 왜 이렇게 되어 있고, 다음에 무엇을 하면 되는지"를 알 수 있게 쓴다.

- **대상 독자:** Track E 팀원, 이 펌웨어를 이어받거나 검토할 사람
- **개념 설명**(마이크로컨트롤러, PWM, PID, 워치독 등)과 **실험 절차**는 가이드 문서
  `docs/02_guide/01_firmware/01_teensy_guide.md`에 있다. 이 문서는 그 내용을 반복하지 않는다.
- **설계의 원본:** `docs/design/dbw.md` §9–12, `docs/design/safety.md`. **절차의 원본:** `docs/build/04-firmware.md`.
  이 문서와 원본이 다르면 원본이 맞다.
- **마지막 갱신:** 2026-11-14 · 브랜치 `firmware/sensing` (테스트 벤치 검증 반영)
- **경로 표기:** 모든 경로는 **저장소 루트** 기준이다. 저장소 밖 경로는 출처(공식 문서의 설치 위치, 도구 기본값)를 함께 적었다.

---

## 1. 한눈에 보기

- **현재 단계:** Stage 0 — **센싱만** 한다. 아무것도 구동하지 않는다.
  - 조향각 센서(AS5600)와 구동 엔코더를 200 Hz로 읽어 ROS 2로 보낸다.
  - 모터 펄스 두 줄은 1500 µs(정지), 릴레이는 LOW(STOCK)로 고정되어 있다.
- **검증 상태**
  - PC 단위 테스트 21개 통과
  - Teensy 4.1 실기 확인(센서 미연결 상태): 안정 동작, `/mitt/dbw/status` 200 Hz, 고장 비트·서비스 거부 정상
  - **책상 위 테스트 벤치 검증 완료 (2026-11-14):** 홀센서 래치·카운트, AS5600 I²C·공극·각도 (7.7절)
  - **차량 장착 후 확인은 아직 안 함** → 다음 작업: 장착, wrap 검사, k·c0 보정, USB 30분 안정성
- **개발 방식:** 기능 하나 = 브랜치 하나. 앞 브랜치 위에 쌓는다.
  `main`(교수님 원본) → `firmware/sensing`(지금) → `firmware/steering` → …
- **다음 단계:** 센서 배선·보정(Stage 0 gate) → 조향 위치 루프(Stage 1)

---

## 2. 개발 원칙

이 펌웨어는 아래 원칙으로 만든다. 코드 리뷰나 다음 단계 작업에서 판단 기준으로 쓴다.

- **문서가 원본이다.**
  - 핀 번호, 수치, 안전 규칙은 `docs/build/04-firmware.md`, `docs/design/*.md`에서 가져온다.
  - 문서에 없는 값을 정할 때는 `mitt_config.h`에 `[POLICY]`로 표시하고 팀이 확정한다.
- **한 번에 한 단계씩 늘린다.**
  - 각 단계는 그 단계의 검증 항목(gate)이 필요로 하는 기능만 넣는다.
  - 이유: 이전에 받은 "한꺼번에 다 넣은" 펌웨어는 Stage 1 시험조차 시작할 수 없는 구조였다(7.4절).
- **판단하는 코드와 핀을 만지는 코드를 나눈다.**
  - 판단 코드(`sensors.*` 등)는 Arduino에 의존하지 않아 PC에서 테스트한다.
  - 하드웨어에서 처음 발견하면 위험한 실수를 책상 위에서 먼저 잡기 위해서다.
- **루프는 절대 기다리지 않는다.**
  - 워치독(250 ms)은 루프 한 바퀴가 끝날 때만 먹이를 준다. 어떤 함수든 오래 막히면 리셋된다.
  - 통신은 확인 응답을 기다리지 않는 best-effort로 한다.
- **출력은 항상 안전한 값에서 시작한다.**
  - 부팅 직후 펄스 1500 µs, 릴레이 LOW. 모터 드라이버가 켜질 때 보는 펄스를 정지로 학습하기 때문이다.
- **버전은 고정한다.**
  - 같은 커밋이 다음 학기에도 같은 펌웨어를 만들어야 한다(`docs/design/software.md` §6.3).

---

## 3. 개발 환경과 버전

문서(`software.md` §6.3)가 요구하는 버전 기록이다. 바꿀 때는 이 표와 함께 커밋한다.

| 구성 요소 | 버전 | 어디에 고정되어 있나 |
|---|---|---|
| OS | Ubuntu 22.04.5 (WSL2) | — |
| ROS 2 | Humble (`ros-humble-ros-base 0.10.0`) | — |
| PlatformIO Core | 6.2.0 | `get-platformio.py`로 설치 (PlatformIO 기본 위치 `~/.platformio/`) |
| PlatformIO Teensy 플랫폼 | `teensy@6.0.0` | `platformio.ini` |
| ↳ Teensyduino 코어 | 1.162 (TD 1.62) | 플랫폼이 결정 |
| ↳ 컴파일러 | arm-none-eabi-gcc 15.2.1 | 플랫폼이 결정 |
| micro-ROS 라이브러리 | `micro_ros_arduino v2.0.8-humble` (`8d527c4`) | `scripts/build_microros_lib.sh` |
| ↳ 라이브러리 빌더 | `microros/micro_ros_static_library_builder` digest `sha256:0d23908…06b0` | 같은 스크립트 |
| ↳ 빌드 설정 | 기본값 + `RMW_UXRCE_MAX_SERVICES=6` | `microros/colcon.meta` |
| 워치독 라이브러리 | `WDT_T4` (`1910b57`) | `platformio.ini` |
| micro-ROS agent (PC) | `micro_ros_setup` humble `9975772`, `micro-ROS-Agent` `c93ee76` | `docs/build/04-firmware.md` §4.2 방식으로 소스 빌드 (기본 위치 `~/uros_ws`) |
| Docker | 29.1.3 (Ubuntu `docker.io`) | 라이브러리 빌드에만 사용 |

- **micro-ROS를 이 방식으로 고른 이유**
  - `dbw.md` §9가 `micro_ros_arduino v2.0.8-humble`을 지정한다.
  - 그런데 배포본에는 우리 메시지(`mitt_msgs`)가 없다. 그래서 공식 Docker 빌더로 `mitt_msgs`를 넣어 **다시 빌드**한다.
  - 결과물(약 20 MB)은 빌드 산출물이라 git에 넣지 않고, 각자 스크립트로 만든다. 무엇으로 만들었는지는
    `lib/micro_ros_arduino/BUILD_INFO.txt`에 자동 기록된다.
- **서비스 개수를 6으로 늘린 이유**
  - Stage 1에서 PID 게인을 ROS 2 파라미터로 바꾸려면 파라미터 서버(서비스 5개)가 필요하다. 영점 서비스까지 6개.
  - 기본값(1개)으로는 불가능하다. Stage 0에는 필요 없지만, 라이브러리를 단계마다 다시 빌드하지 않으려고 미리 늘렸다.

---

## 4. 저장소 구성

```
firmware/
├── .gitignore                  빌드 산출물 제외 (.pio/, .host_build/, lib/micro_ros_arduino/)
├── bench/                      배선 단계별 검증 스케치 (스케치 하나 = 기능 하나)
│   ├── platformio.ini          upload_protocol = teensy-cli 추가
│   └── src/                    i2c_scan, as5600_check, quad_count (교수님 저장소에 이미 있음)
└── mitt_dbw/                   본 펌웨어
    ├── platformio.ini          빌드 환경: mitt_dbw, uros_echo
    ├── include/mitt_config.h   모든 숫자 (핀, 주기, 보정값, 판단 기준)
    ├── src/                    펌웨어 소스 (5장)
    ├── test/host/              PC 단위 테스트
    ├── scripts/build_microros_lib.sh   micro-ROS 라이브러리 재생성
    ├── microros/colcon.meta    라이브러리 빌드 설정
    └── COLCON_IGNORE           ROS 워크스페이스 빌드가 이 폴더를 건너뛰게 함
```

- **커밋된 것:** 위 트리 전체(산출물 제외)
- **아직 커밋하지 않은 것 (해당 단계에서 커밋 예정)**
  - `bench/src/pwm_effort_check.cpp` — Stage 1 (출력 부호, PWM 주기, hang 테스트)
  - `bench/src/ibus_monitor.cpp` — Stage 2 (RC 수신기)
  - `bench/src/estop_relay_check.cpp` — E-stop 단계
  - 세 파일 모두 이전 작업에서 만들어졌고, 빌드는 확인했지만 하드웨어 검증은 안 됐다.
- **저장소 밖에 보관 중 (개발자 PC)**
  - 저장소 옆 폴더 `../mrider-wip/mitt_dbw_steer_drive_2026-11-13/` — Stage 1 조향 루프 + 구동 채널 코드
    (테스트 104개 통과). **이 PC에만 있고 다른 팀원 PC에는 없다.** 필요하면 해당 단계 브랜치로 옮겨 공유한다.
    7.5절 참고.
  - 저장소 루트의 `mitt_dbw_firmware.patch` — 이전 에이전트가 만든 전체 버전(E-stop, RC 포함). 참고용.

---

## 5. 펌웨어 구조 (Stage 0)

### 5.1 데이터 흐름

```
AS5600 (I²C, 핀 18/19) ──raw 0..4095──▶ calib::RawToRad ──θ──▶ AngleCheck ──▶ 믿을 수 있나? (faults)
                                          θ = k·(raw − c0)
구동 Hall 래치 (QDC, 핀 0/1) ──ticks──▶ × kDriveTicksSign ──▶ WheelSpeed ──▶ m/s
                                                                     │
                                       uros::Publish (200 Hz) ◀──────┘
                                         ├─ /mitt/dbw/status
                                         └─ /mitt/dbw/debug
노트북 ──/mitt/dbw/zero_steering──▶ 현재 raw를 c0로 EEPROM에 저장
```

### 5.2 파일별 역할

| 파일 | 역할 | Arduino 의존 | PC 테스트 |
|---|---|---|---|
| `include/mitt_config.h` | 모든 숫자. 태그로 출처 표시 | 없음 | — |
| `src/sensors.*` | `AngleCheck`(각도 신뢰 판단), `WheelSpeed`(속도 계산) | 없음 | ✅ |
| `src/calibration.*` | c0 EEPROM 저장·복원, raw → rad 변환 | EEPROM | — |
| `src/hal.*` | 핀 입출력: AS5600 읽기, 엔코더 읽기, 펄스 고정, 워치독 | 있음 | — |
| `src/uros_node.*` | micro-ROS: 토픽·서비스, agent 연결·재연결 | 있음 | — |
| `src/main.cpp` | 부품 연결, 200 Hz 루프 | 있음 | — |
| `src/uros_echo.cpp` | 별도 빌드 환경: 핀을 쓰지 않는 통신 테스트 | 있음 | — |

### 5.3 부팅 순서 (`setup()`)

1. **워치독 시작** — 어떤 출력보다 먼저 (`safety.md` §2 row 8)
2. **안전한 출력** — 릴레이 LOW, 펄스 두 줄 정확히 1500 µs
3. **입력 초기화** — I²C 100 kHz, 엔코더 디코더
4. **영점 불러오기** — EEPROM에 저장된 c0, 없으면 기본값
5. **micro-ROS 준비** — agent는 루프에서 찾는다 (없어도 부팅은 끝난다)

### 5.4 루프 (`loop()`, 5 ms = 200 Hz)

- 한 틱에서 하는 일
  1. AS5600 읽기 → 각도 계산 → `AngleCheck` 갱신
  2. 엔코더 읽기 → `WheelSpeed` 갱신
  3. 핀 13 토글 (오실로스코프로 루프 주기 확인용)
  4. **워치독 먹이 주기** — 모든 센서를 다 읽은 뒤에만
- 틱 사이에 micro-ROS를 돌린다. 연결 과정처럼 시간이 걸리는 작업은 단계마다 틱을 끼워 넣어(`between()`)
  루프와 워치독이 멈추지 않게 한다.
- 5 ms마다 상태를 보낸다(agent가 연결되어 있을 때만).
- **타이머 인터럽트를 쓰지 않는 이유:** 인터럽트에서 워치독을 먹이면 메인 루프가 멈춰도 계속 먹여서 워치독이
  무의미해진다.

### 5.5 인터페이스

- **`/mitt/dbw/status`** (`mitt_msgs/DbwStatus`, best-effort, 200 Hz)

  | 필드 | Stage 0 값 |
  |---|---|
  | `stamp` | agent와 시간 동기화 후 노트북 시각 기준 |
  | `steering_angle` | rad, 왼쪽 + . 센서가 대답하면 현재값(범위 밖이어도 표시), 아니면 마지막 정상값 |
  | `steering_setpoint` | 0 (명령 기능 없음) |
  | `wheel_speed` | m/s, 200 ms 창 |
  | `drive_ticks` | 엔코더 누적값 (부호 보정) |
  | `mode` | 항상 0 (ESTOP) |
  | `faults` | 각도를 믿을 수 없으면 1 (`FAULT_ENCODER`), 아니면 0 |

- **`/mitt/dbw/debug`** (`std_msgs/Float32MultiArray`, 200 Hz) — `data[]` 순서

  | 0 | 1 | 2 | 3 | 4 |
  |---|---|---|---|---|
  | AS5600 raw | I²C 응답 (0/1) | 자석 정상 (0/1) | c0 | 직전 리셋이 워치독 (0/1) |

  - 단계가 늘면 뒤에 항목을 덧붙인다. 앞 번호의 의미는 바꾸지 않는다.
- **`/mitt/dbw/zero_steering`** (`std_srvs/Trigger`)
  - 지금 raw를 c0로 EEPROM에 저장하고 `c0 이전값 -> 새값`을 돌려준다.
  - 센서가 정상이 아니면 거부한다.
  - 저장한 값은 `config/calibration/steering.yaml`에도 적는다(`calibration.md` §1).

### 5.6 센서 판단 규칙 (`AngleCheck`)

`safety.md` §2 row 9 "매 주기 타당성·범위 검사, 나쁜 각도로는 절대 루프를 돌리지 않는다"를 구현한다.
매 샘플을 아래 순서로 검사하고, 하나라도 걸리면 그 즉시 "믿을 수 없음"이 된다.

- I²C가 대답하지 않음
- 자석 상태가 정상이 아님 (없음 / 너무 약함 / 너무 강함)
- 각도가 숫자가 아님 (NaN)
- |각도| > 22.5° + 3° (물리적으로 불가능)
- 한 틱(5 ms)에 3° 넘게 변함 (600°/s, 사실상 wrap이나 잡음)
- **다시 믿으려면** 정상 샘플이 **200 ms 연속**이어야 한다. 한 번 튄 값 뒤에 바로 믿었다가 다시 놓치는
  깜빡임을 막는다.

### 5.7 설정값 (`mitt_config.h`)

- 태그
  - `[FROZEN]` 문서에서 고정 — 바꾸지 않는다 (핀 번호, ±22.5°)
  - `[SPEC]` 설계 문서 값 — 문서가 바뀔 때만 (200 Hz, 1500 µs)
  - `[MEASURE]` 차량에서 측정해 채울 값 — **지금은 자리표시자**
  - `[POLICY]` 문서에 없어 정한 값 — 팀 확정 필요
- Stage 0에서 측정해 채울 값
  - `kSteerDegPerCount` (배율 k, 부호 포함)
  - `kSteerC0Default` (영점; 실제로는 서비스로 EEPROM에 저장)
  - `kDriveTicksSign`, `kTicksPerWheelRev`, `kWheelCircumferenceM`
  - `kPwmFrameHz` (Stage 1)

### 5.8 테스트

- `./test/host/run_host_tests.sh` — `sensors.cpp`를 PC용으로 컴파일해 21개 항목을 확인한다.
  - 각도: 부팅 직후 불신, 200 ms 후 신뢰 · I²C/자석 실패 즉시 고장 · 한 번 실패 후 200 ms 재대기 ·
    범위 밖 · 3° 점프 · NaN · `micros()` 랩어라운드
  - 속도: 1 rev/s → 둘레 길이 · 역방향 부호 · 정지 시 0 · 랩어라운드
- **테스트가 실제로 잡는지 확인하는 습관 (mutation check)**
  - 규칙 하나를 일부러 지운 코드로 테스트를 돌려, 실패가 나오는지 본다.
  - 예: 3° 점프 검사를 지우면 해당 테스트가 실패한다(확인함). 실패가 안 나오면 테스트가 그 규칙을 못 지키는 것이다.

---

## 6. 빌드·검증 절차

새 기능을 커밋하기 전에 아래를 모두 통과시킨다.

1. **PC 테스트** — `./test/host/run_host_tests.sh` → `N passed, 0 failed`
2. **빌드** — `pio run -e mitt_dbw`, `pio run -e uros_echo` → `SUCCESS`, 우리 소스(`src/`)에서 경고 없음
3. **bench 빌드** — `firmware/bench`에서 `pio run` (CI가 이 프로젝트를 빌드한다)
4. **업로드** — `pio run -e mitt_dbw -t upload` (첫 시도 실패 시 한 번 더)
5. **실기 확인** — agent를 켜고
   - agent 없이 30초 이상 재부팅 없음 (`lsusb`로 확인)
   - `ros2 topic hz /mitt/dbw/status` ≈ 200 Hz
   - status/debug 값이 그 단계에서 기대하는 값인지
6. **커밋** — 검증 결과를 커밋 메시지에 적는다

- 새 PC에서 처음이면 먼저 `./scripts/build_microros_lib.sh`로 라이브러리를 만든다(Docker 필요).

---

## 7. 개발 과정 기록

### 7.1 출발점 (2026-11-12)

- 교수님 저장소에는 펌웨어가 없었다(`docs/course/teams.md`: "firmware/ — Does not exist").
- 이전 AI 에이전트가 만든 `firmware/mitt_dbw`가 git 밖에 있었다. 상태는 다음과 같았다.
  - E-stop, RC, 조향, 구동, 워치독까지 **한 번에 전부** 들어 있음
  - micro-ROS를 문서가 정한 `micro_ros_arduino` 대신 `micro_ros_platformio`(소스 빌드)로 바꿔 놓음
  - 그 결과 GCC 15(teensy@6.0.0)에서 micro-ROS 빌드가 실패(`clock_gettime` 암시적 선언 오류)
  - 이를 피하려고 플랫폼을 `teensy@5.1.0`으로 내리는 우회를 시도하던 중
- **결정:** 우회를 멈추고 **문서가 정한 버전으로 돌아간다.**
  - 근거: `dbw.md` §9, `software.md` §6.3의 버전 고정 요구
  - 확인: 문서 버전 조합(`teensy@6.0.0` + `micro_ros_arduino v2.0.8-humble`)으로 최소 테스트 펌웨어를 빌드·업로드해
    agent와 10 Hz 통신 성공 → **문서 방식으로 문제없음**

### 7.2 커스텀 메시지 포함 라이브러리

- `micro_ros_arduino` 배포본에는 `mitt_msgs`가 없어 `DbwStatus`를 보낼 수 없다.
- 공식 Docker 빌더에 `ros2_ws/src/mitt_msgs`를 넣어 `teensy4` 대상으로 다시 빌드했다.
- 이 과정을 `scripts/build_microros_lib.sh`로 만들어, 누구나 같은 결과를 얻게 했다(빌더 이미지 digest 고정).

### 7.3 워치독 리셋 반복 버그

- **증상:** 이전 전체 버전을 올렸더니, 아무것도 연결하지 않은 상태에서 8~10초마다 재부팅했다.
- **처음 추정과 실제**
  - 추정: 크래시(hard fault). Teensy 4는 크래시 후 8초 뒤 재부팅하므로 주기가 맞아 보였다.
  - 진단 1: 부팅 직후 `CrashReport`를 출력하는 진단 빌드 → **CrashReport 없음**, `setup()`은 끝까지 완료.
    → 크래시가 아니다.
  - 진단 2: 루프 각 부분의 최대 소요 시간을 출력 → PC가 포트를 열어 읽고 있을 때는 정상(최대 10 ms),
    포트를 닫으면 재부팅. → **"USB는 꽂혀 있는데 아무도 포트를 안 열었을 때"** 가 조건.
- **원인**
  - `micro_ros_arduino`의 `arduino_transport_open()`이 `Serial.begin()`을 부른다.
  - Teensy 4의 `Serial.begin()`은 PC가 포트를 열 때까지 **최대 2초 기다린다.**
  - agent 확인(ping)을 500 ms마다 할 때마다 이 함수가 불려, 250 ms 워치독이 리셋했다.
  - 이전 버전은 `micro_ros_platformio` 기준이라 이 경로가 한 번도 시험되지 않았다.
- **수정:** 라이브러리가 교체용으로 열어 둔(`weak`) `arduino_transport_open()`을 "즉시 true 반환"으로 바꿨다
  (`uros_node.cpp`). Teensy의 USB 시리얼은 `begin()`이 필요 없다.
- **교훈**
  - 워치독이 있는 펌웨어에서는 라이브러리 함수도 "얼마나 오래 막힐 수 있나"를 확인해야 한다.
  - 추정이 그럴듯해도 측정으로 확인한다(이번에는 첫 추정이 틀렸다).

### 7.4 문서와 이전 펌웨어 점검 결과

| 항목 | 내용 | 처리 |
|---|---|---|
| Stage 1을 시작할 수 없음 | ESTOP을 벗어나려면 RC 수신기·E-stop 회로가 모두 필요했는데, 문서상 RC는 Stage 2 | 문서 자체의 순서 공백. 단계별로 다시 만들어 해소 |
| PID 게인이 상수 | 문서는 "게인은 ROS 2 파라미터로"(`dbw.md` §10.1) | Stage 1 코드에서 파라미터로 구현해 둠(보관 중) |
| 상태 100 Hz | 스텝 응답은 "≥ 200 Hz로 기록"(`04-firmware.md` §4.4) | 200 Hz로 변경 |
| 펌웨어가 git 밖 | 측정 기록에 "펌웨어 커밋"을 남겨야 함(`06-bench-test.md`) | 단계별 커밋 시작 |
| 정의 안 된 고장 비트 | 64/128/256을 펌웨어만 사용, `DbwStatus.msg`에 없음 | 해당 기능 단계에서 메시지 정의와 함께 추가 |
| `[POLICY]` 값 다수 | 모드 스위치(CH6), arm 방식, stall 임계 등 문서에 없는 결정 | 해당 단계에서 팀 확정 |

### 7.5 범위 축소: Stage 0부터 다시

- **결정 (2026-11-13):** 펌웨어를 **센싱만** 하는 상태로 줄이고, 단계마다 기능과 배선을 함께 늘린다.
- **이유**
  - 한꺼번에 넣은 기능은 검증 순서와 맞지 않아 오히려 시험을 막았다.
  - 배선이 아직 없으므로, 지금 확인할 수 있는 것(센서)만 코드에 있어야 확인 결과가 의미가 있다.
- **보관한 것:** Stage 1 조향 루프와 구동 채널은 이미 작성·테스트했다. 다음 단계에서 재사용하기 위해 저장소 밖에
  보관했다(4장). 내용은 다음과 같다.
  - 조향: PID(실행 중 게인 변경), `enable` 파라미터로 의도적 허가, 한계 클램프, stall, 명령 끊김 시 중앙 복귀 후 정지,
    센서 고장 시 즉시 정지
  - 구동: 속도 상한, 가감속 제한, 바퀴 속도 계산, 대기 상태에서 즉시 0
  - 테스트: 조향 81개, 구동 23개

### 7.6 Stage 0 검증 결과 (2026-11-13, 센서 미연결)

- PC 테스트 21개 통과, 규칙 하나를 지운 변형 코드는 테스트가 실패로 잡음
- `mitt_dbw`, `uros_echo` 빌드 성공, 우리 소스 경고 0
- Teensy 실기
  - agent 없이 재부팅 없음
  - `/mitt/dbw/status` 199.6 Hz
  - `mode 0`, `faults 1` (센서 없음 → 정상)
  - debug: raw 0, I²C 0, 자석 0, c0 2048, 워치독 리셋 0
  - 영점 서비스: "AS5600 not healthy"로 거부 (정상)

### 7.7 테스트 벤치 검증 (2026-11-14, 책상 위)

- **결과:** 검증 방법과 기록은 `docs/03_validation/01_firmware/test_bench.md`
  - 홀센서 A·B: 자석에 따라 OUT 0 V ↔ 3.3 V 래치 동작, `quad_count`에서 순서대로 대면 count 증가
  - AS5600: `i2c_scan` `PASS 0x36 alone.`, `as5600_check` 공극·각도 확인
- **겪은 문제와 해결**
  - **홀센서가 자석에 반응 없음, VCC–OUT 2 V:** DRV5013을 반대로 꽂아 VCC와 OUT이 바뀜.
    진짜 VCC가 10 kΩ 풀업을 거쳐서만 전원을 받아 동작 전압(2.5 V) 미만이었다. 인쇄면(TO-92 사다리꼴의 **좁은 쪽**)을
    보고 왼쪽부터 1 VCC · 2 GND · 3 OUT으로 다시 꽂아 해결(TI SLIS150N Figure 4-2·8-3).
  - **회로도 보완:** 데이터시트와 `03-electrical.md` §3.5.4가 요구하는 래치별 100 nF 바이패스(C3·C4)가 빠져 있어 추가.
  - **`i2c_scan`이 아무것도 출력하지 않고 업로드에도 무응답:** 배선 재점검(SDA·SCL 3.3 V, 18·19–GND 약 15 kΩ) 후
    USB를 다시 꽂자 정상 동작. 앞서 SDA가 0 V로 측정됐던 배선 문제와 관련된 것으로 추정(정확한 원인은 미확인).
  - **`pio device monitor`가 포트 번호를 물음:** 업로드 직후 WSL 재연결(10~15초) 전에 모니터가 시작돼서.
    `firmware/bench/platformio.ini`에 `monitor_port = /dev/ttyACM*` 추가.
- **회로도:** `docs/02_guide/01_firmware/images/stage0_bench_schematic.svg` (Teensy 실제 핀 배치 기준, 생성 스크립트 동봉)

---

## 8. 브랜치와 커밋 규칙

- **원격 저장소**
  - `origin` = 교수님 저장소(`jrkwon/mrider`). 읽기 전용, push 차단(`no_push`).
  - `team` = 팀 저장소. 우리 작업을 올리는 곳.
- **브랜치**
  - `main` = 교수님 원본과 동일하게 유지. 교수님 업데이트를 받는 용도.
  - 기능 브랜치를 앞 단계 위에 쌓는다.
    ```
    main
     └─ firmware/sensing        Stage 0 센싱 (지금)
         └─ firmware/steering   Stage 1 조향 위치 루프
             └─ firmware/drive  구동 채널 …
    ```
  - 다음 브랜치 시작: `git switch -c firmware/steering firmware/sensing`
- **교수님 업데이트 받기**
  - `git fetch origin` → `main`을 `origin/main`으로 앞으로 이동 → `git push team main`
  - 작업 브랜치는 필요할 때 새 `main` 위로 옮긴다(`git rebase main`). 이미 팀원과 공유한 브랜치라면 `merge`를 쓴다.
- **커밋**
  - 한 커밋 = 검증이 끝난 기능 하나. 6장의 절차를 통과한 뒤 커밋한다.
  - 메시지에 무엇을, 왜, 어떻게 검증했는지 적는다.
  - AI 도구를 쓴 경우 메시지에 밝힌다(수업 규정 `docs/course/syllabus.md`).
  - 측정 기록(`docs/build/validation-report.md` 등)에는 그때의 커밋 해시를 적는다. 그래서 **측정 전에 커밋**한다.
- **GitHub Actions**
  - 교수님 저장소의 자동 작업(문서 배포, 빌드 검사)이 팀 저장소에서도 `main` push 때 실행되어 실패 메일이 온다.
  - 팀 저장소에서 Settings → Actions → "Disable actions"로 끄는 것을 권장.

---

## 9. 다음 단계 로드맵

| 브랜치 | 추가할 것 | 함께 할 배선 | 통과 기준 (gate) |
|---|---|---|---|
| `firmware/sensing` (지금) | — | AS5600, Hall 래치 2개, 풀업 | wrap 없음, k·c0 측정, 센서 뽑으면 고장 비트, 엔코더 방향, USB 30분 끊김 0 |
| `firmware/steering` | 명령 수신, 조향 PID, 파라미터(게인·`enable`), 한계·stall·끊김 규칙, hang 테스트 빌드 | MDDS30(RC1), 조향 모터, 전류 제한 전원, 신호 MUX | 정상상태 오차 ≤ 1°, 스텝·RMS·드리프트 기준, 안전 동작, hang 테스트 → **Merge 1 (11/23)** |
| `firmware/drive` | 구동 채널(속도 상한·가감속 제한), 바퀴 속도 활용 | RC2, 후륜 모터 (바퀴 띄움) | 명령 속도 추종, 끊김 시 즉시 정지 |
| `firmware/rc` | i-BUS 해석, MANUAL_RC 모드, RC arm | RC 수신기(전압 확인 후), 신호 MUX SEL | Layer A 200 ms 이내 전환, RC 상실 → ESTOP, Layer B는 Teensy 정지 상태로 시험 |
| `firmware/estop` | E-stop 감지, hold-off, 재허가 규칙, 릴레이 | E-stop 분압 회로, 릴레이 MUX | 눌림/해제/선 빠짐 동작, 해제 시 움직임 없음 (`06-bench-test.md` row 5a) |

- **단계별로 결정이 필요한 것**
  - steering: Stage 1에서 RC 없이 무엇으로 허가할지 → 보관 코드는 `enable` 파라미터 사용
  - steering: 신호 MUX가 RC 수신기 없이 어느 입력을 고르는지(Pololu 2806 설명서 확인) — 문서에 없음
  - rc: 모드 스위치 채널과 arm 동작(`[POLICY]`), 송신기 failsafe 설정
  - estop: 릴레이를 DBW로 붙이는 조건, `DbwStatus.msg`에 E-stop 비트 추가 여부

---

## 10. 알려진 문제와 주의

- **업로드 첫 시도 실패**: WSL에서 program 모드로 바뀌는 순간 usbipd 재연결 때문. 다시 실행하면 된다.
- **usbipd auto-attach가 `Failed to attach`를 반복**: 실행 중인 attach를 멈추고 다시 실행.
- **`VUSB`–`VIN` 분리 후**: USB만으로는 Teensy가 켜지지 않는다. UBEC 5 V를 `VIN`에 넣어야 한다.
- **bench 스케치의 보정값 복사본**: `pwm_effort_check.cpp`는 `kSteerDegPerCount`를 따로 들고 있다. 측정값을 바꾸면
  두 곳을 같이 바꾼다.
- **`[MEASURE]` 값은 아직 전부 자리표시자다.** 측정 전에는 각도·속도의 절대값을 믿지 않는다.

---

## 11. 참고 문서

- 설계: `docs/design/dbw.md` §9–12 (펌웨어 플랫폼, 인터페이스, 상태 머신, 수치 계약)
- 안전: `docs/design/safety.md` §1 (권한 우선순위), §2 (failsafe 표), §6 (단계별 bring-up)
- 절차: `docs/build/04-firmware.md` (핀 표, Stage 0–2), `docs/build/03-electrical.md` §3.5 (신호 배선, 브레드보드)
- 보정: `docs/design/calibration.md` §1 (조향 영점·배율), §2 (주행거리)
- 일정: `docs/course/teams.md` (Merge 일정)
- 가이드: `docs/02_guide/01_firmware/01_teensy_guide.md`

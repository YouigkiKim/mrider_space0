# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어

- **모든 답변은 한국어로만 작성한다.** 중간 진행 보고, 요약, 설명, 질문 모두 포함한다.
- 코드, 명령어, 파일 내용(식별자·주석·커밋 메시지)은 원래 쓰던 언어 그대로 둬도 된다.
- 긴 작업 도중이나 짧은 질의응답에서도 영어로 바뀌지 않도록 보내기 전에 확인한다.

## 저장소 개요

- MRider: 아이용 전동차를 DBW(drive-by-wire) 자율주행 플랫폼으로 바꾸는 연구·교육 프로젝트. 원본은 교수님 저장소
  `jrkwon/mrider`이고 문서 사이트(MkDocs)가 `main` push 때 배포된다.
- 이 클론은 **Track E(전장·펌웨어) 팀 작업용**이다.
  - `origin` = 교수님 저장소(읽기 전용, push 차단 `no_push`), `team` = 팀 저장소.
  - `main` = **팀 통합 브랜치**로, 교수님 원본과 다르다. 검증이 끝난 기능 브랜치를 PR로 합친다.
  - 작업은 기능 브랜치를 앞 단계 위에 쌓는다: `firmware/sensing`(Stage 0) → `firmware/steering`(Stage 1) → …
  - 교수님 업데이트는 **pull만** 받는다: `git switch main && git pull origin main && git push team main`.
    충돌은 그 부분만 정리하고, push한 `main`은 다시 쓰지 않는다(`rebase`, `push --force` 금지).
  - push와 PR 생성은 사용자가 직접 한다(이 환경에는 GitHub 인증과 `gh`가 없다).
  - `main`에 push하면 교수님 저장소에서 따라온 GitHub Actions(문서 배포 등)가 팀 저장소에서 돌아 실패 메일이 갈 수 있다.
- **설계·절차의 원본:** `docs/design/`(ADR, `dbw.md`, `safety.md`, `calibration.md`, `software.md`),
  `docs/build/`(단계별 절차, 특히 `04-firmware.md` 핀 표·Stage 0–2), `docs/course/`(수업·merge 일정).
  수치·핀·안전 규칙은 여기서 가져오고, 문서에 없는 값은 `[POLICY]`로 표시해 팀이 확정한다.

## 주요 명령

### 문서 (MkDocs)
```bash
pip install -r requirements-docs.txt
mkdocs serve                       # 로컬 미리보기
bash scripts/check_docs.sh         # push 전 전체 검사 (mkdocs --strict, 앵커, 그림 최신 여부, 배선 일관성 등 20여 개)
python3 scripts/check_anchors.py site   # --strict가 놓치는 깨진 #앵커 (mkdocs build 뒤)
```
- 경고 상자는 GitHub 문법 `> [!NOTE]`/`> [!WARNING]` 등으로 쓴다. `hooks/github_alerts.py`가 사이트용으로 바꾼다.
  MkDocs 전용 `!!!`는 쓰지 않는다.
- `docs/images/`의 그림 상당수는 `scripts/gen_*.py`가 만든다. 생성기를 고치면 다시 실행해야 검사(그림 최신 여부)를 통과한다.
- `light` 브랜치는 `main` 위의 얇은 덮어쓰기다(`docs/light/`, `mkdocs.yml`만 다름).

### 수업 도구 테스트
```bash
python3 -m pytest scripts/tests -q                     # 전체
python3 -m pytest scripts/tests/test_grading.py -q -k <이름>   # 하나만
python3 scripts/lab_report.py selftest
```

### ROS 2 워크스페이스 (Humble)
```bash
cd ros2_ws && colcon build
source setup_env.sh                # 모든 터미널마다. RMW를 fastrtps로 강제 — 빠뜨리면 토픽이 안 보여 시뮬레이터가 죽은 것처럼 보인다
ros2 launch mitt_bringup sim.launch.py             # Gazebo Harmonic 디지털 트윈
ros2 launch mitt_navigation slam.launch.py         # 또는 localization.launch.py map:=…, nav2.launch.py
ros2 launch mitt_control teleop.launch.py
```

### 펌웨어 (Teensy 4.1, PlatformIO)
```bash
# firmware/mitt_dbw — 본 펌웨어
./scripts/build_microros_lib.sh    # 새 PC에서 처음, 또는 ros2_ws/src/mitt_msgs 변경 시 (Docker, ~5분). lib/는 git 무시
./test/host/run_host_tests.sh      # 판단 코드 PC 단위 테스트 (g++)
pio run -e mitt_dbw                # 빌드 / -t upload 로 업로드
# firmware/bench — 배선 단계별 검증 스케치 (스케치 하나 = env 하나). CI가 이 프로젝트 전체를 teensy@6.0.0으로 빌드
pio run -e i2c_scan -t upload && pio device monitor
```
- WSL에서는 Teensy를 `usbipd attach --wsl --busid <id> --auto-attach`로 붙인다. busid는 꽂은 포트마다 다르다.
- 업로드 첫 시도는 재연결 때문에 자주 실패하므로 한 번 더 실행한다. 시리얼 포트는 한 번에 한 프로그램(모니터, agent, 업로더)만 쓸 수 있다.
- micro-ROS agent: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200` (agent는 `docs/build/04-firmware.md` §4.2 방식으로 소스 빌드).

## 아키텍처 큰 그림

- **DBW 데이터 경로:** 노트북(ROS 2) ↔ micro-ROS agent ↔ USB ↔ Teensy 4.1.
  - 노트북 → Teensy: `/mitt/dbw/command` (`mitt_msgs/DbwCommand`). Teensy → 노트북: `/mitt/dbw/status` (`DbwStatus`).
  - Teensy가 200 Hz 조향 위치 루프를 돌리고 서보 PWM(핀 2·3) → 신호 MUX → MDDS30(RC1 조향, RC2 구동)으로 낸다.
  - 센서는 AS5600 조향 절대각(I²C 18·19), 구동 엔코더 Hall 래치(QDC 0·1), IMU BNO085(두 번째 I²C `Wire1`,
    SDA1 17·SCL1 16 — 2026-11-16 원본 결정, `docs/design/sensors.md` §3). IMU 읽기는 조향 루프를 늦추면 안 된다.
- **안전은 겹으로 되어 있다** (`docs/design/safety.md`):
  - 하드웨어가 멈춘다: E-stop, 릴레이 MUX(기본 STOCK), 신호 MUX(Layer B).
  - 펌웨어는 함부로 재출발하지 않는다: E-stop 감지, 재허가(arm), 끊김 감시, 워치독.
- **`mitt_msgs`는 두 곳에서 쓰인다:** ROS 워크스페이스, 그리고 펌웨어 micro-ROS 라이브러리(빌드할 때 넣음).
  메시지를 바꾸면 `colcon build`와 `build_microros_lib.sh`를 둘 다 다시 실행한다.
- **ROS 2 패키지(`ros2_ws/src/mitt_*`):** description(URDF), sim(Gazebo), control(ros2_control·teleop),
  localization(EKF), navigation(slam_toolbox·Nav2), bringup(launch), msgs.
  ADR-SW4: 시뮬레이터와 실차는 같은 스택을 쓰고 **ros2_control 하드웨어 플러그인만** 다르다.
- **펌웨어 구조 (`firmware/mitt_dbw`):**
  - `include/mitt_config.h`에 모든 수치. 태그 `[FROZEN]/[SPEC]/[MEASURE]/[POLICY]/[TUNE]`로 출처를 표시한다.
  - **판단 코드**(Arduino 무의존, `test/host`에서 테스트)와 **핀 코드**(`hal.*`)를 분리한다.
  - `loop()` 안의 200 Hz 폴링 루프로 돈다. 워치독(250 ms)은 한 바퀴를 끝낸 뒤에만 먹인다(타이머 인터럽트 금지).
  - **루프는 절대 기다리지 않는다:** 퍼블리시는 best-effort. `micro_ros_arduino`의 `arduino_transport_open()`은 Teensy에서
    `Serial.begin()`이 최대 2초 막히므로 즉시 반환하도록 재정의했다.
  - 버전 고정: `teensy@6.0.0`, `micro_ros_arduino v2.0.8-humble`(빌더 이미지 digest 고정).
  - 펌웨어는 **단계마다 기능을 하나씩** 늘린다(현재 Stage 0 센싱). 다음 단계 코드(조향 루프·구동)는 저장소 밖
    `../mrider-wip/`, 이전 전체 버전은 루트의 `mitt_dbw_firmware.patch`(커밋 안 함)에 참고용으로 있다.
- **수업 도구:** `scripts/lab*.py`, `lab.sh`. 학생 번들에는 채점기(`lab_grading.py`)가 들어가면 안 된다(`check_lab_modules.py`가 검사).

## 커밋

- 한 커밋에 검증이 끝난 기능 하나를 담고, 메시지에 무엇을·왜·어떻게 검증했는지 적는다.
- AI 도구를 쓴 경우 메시지에 밝힌다(`docs/course/syllabus.md`).
- 측정 기록에는 그때의 펌웨어 커밋 해시를 적는다(`docs/build/06-bench-test.md`). 그래서 측정 전에 커밋한다.
- 커밋하지 않는 것: 빌드 산출물(`firmware/.gitignore`), `BUILD_TEENSY.md`, `mitt_dbw_firmware.patch`, 해당 단계가 아닌
  bench 스케치(`ibus_monitor`, `estop_relay_check`, `pwm_effort_check`는 그 단계에서 커밋).

## 문서화 가이드

개발하면서 생기는 팀 문서는 `docs/` 아래 번호가 붙은 세 폴더에 둔다.
교수님 원본 문서(`docs/build/`, `docs/design/`, `docs/course/` 등)는 **고치지 않고 참고만** 한다.
원본과 팀 문서가 다르면 원본이 기준이며, 다른 이유를 팀 문서에 적는다.

### 폴더 구조와 역할

```
docs/
├── 01_development/      개발 기록 — 무엇을, 왜 이렇게 만들었나
│   ├── 01_firmware/
│   └── 02_power_wire/
├── 02_guide/            가이드 — 개념과 사용법, 어떻게 하나
│   ├── 01_firmware/
│   └── 02_power_wire/
└── 03_validation/       검증 — 확인 방법과 결과
    └── 01_firmware/
```

| 폴더 | 읽는 사람 | 넣을 내용 | 넣지 않을 내용 |
|---|---|---|---|
| `01_development/` | 팀원, 이어받을 사람 | 현재 상태 요약, 구조(코드·회로), 고정한 버전, **개발 과정과 결정 이유**(문제 → 진단 → 원인 → 해결 → 교훈), 브랜치·커밋, 다음 단계 로드맵, 알려진 문제 | 개념 설명, 단계별 사용법 |
| `02_guide/` | 처음 배우는 사람 | 개념("왜"), 단계별 방법("어떻게": 명령, 기대 출력, 막혔을 때), 그림, 명령어 설명 | 실험 기록, 측정 결과 |
| `03_validation/` | 검토자, merge 데모 | **간단한 검증 방법**, 통과 기준, 결과 기록표(측정값, 날짜, 펌웨어 커밋 해시) | 긴 설명(가이드로 링크) |

- **주제 폴더:** `01_firmware`는 Teensy 펌웨어, bench 스케치, micro-ROS, 신호 기판(벤치를 옮긴 Teensy 소켓 기판)을 다룬다. `02_power_wire`는 전원 레일, 하네스, E-stop·릴레이, 신호 배선을 다룬다.
- 새 주제가 생기면 다음 번호(`03_…`)로 세 폴더에 필요한 만큼 만든다. 빈 폴더에는 `.gitkeep`을 둔다.
- 현재 문서
  - `01_development/01_firmware/01_firmware_development.md` — 펌웨어 구조와 개발 기록
  - `01_development/01_firmware/02_steering_design.md` — 조향 펌웨어 설계 (1차 RC 조향 → 2차 컴퓨터 조향), 결정 대기 항목
  - `01_development/01_firmware/03_signal_board_design.md` — 신호 기판(Teensy 소켓 만능기판) 설계, 원본과 다른 점
  - `02_guide/01_firmware/01_teensy_guide.md` — Teensy 개념과 단계별 bring-up 방법
  - `02_guide/01_firmware/02_rc_receiver_guide.md` — RC 수신기(FS-iA6B) 핀 구조, 연결, 바인딩, `ibus_monitor`
  - `02_guide/01_firmware/03_signal_board_guide.md` — 신호 기판 납땜 순서 (배치도는 원본 생성기 데이터로 생성)
  - `03_validation/01_firmware/test_bench.md` — Stage 0 테스트 벤치 검증 방법과 결과
  - `03_validation/01_firmware/02_steering_bench.md` — 조향 단계 벤치 검증 방법과 결과 (i-BUS 대기 전압, 수신)
  - `03_validation/01_firmware/03_signal_board.md` — 신호 기판 단락·도통·전압 검사와 결과

### 작성 규칙

- **한국어**로, 다른 사람이 읽기 쉽게 논리적인 순서로 쓴다. 불릿과 표를 적극적으로 쓴다.
- **파일 이름:** `NN_이름.md` (NN은 두 자리 순서). 그림은 문서 옆 `images/`에 둔다.
  그림을 스크립트로 만들었다면 스크립트도 함께 두고 사용법을 맨 위에 적는다.
- **경로:** 본문의 경로는 저장소 루트 기준으로 쓴다(`firmware/bench`). 문서끼리의 링크는 그 파일 기준 상대 링크로 쓴다.
  `~/git/mrider`나 사용자 이름처럼 특정 PC에만 맞는 경로는 쓰지 않는다. 저장소 밖 경로는 출처(공식 문서의 설치 위치 등)를 함께 적는다.
- **출처:** 수치·핀·규칙은 원본 문서의 위치를 적는다(예: `docs/build/04-firmware.md` §4.3). 데이터시트를 인용하면 문서 번호와 그림·표 번호를 적는다.
- **중복 금지:** 같은 내용을 세 폴더에 복사하지 않는다. 개념은 가이드, 결정 이유는 개발 기록, 방법·결과는 검증 문서에 두고 서로 링크한다.
- **측정값:** 날짜와 그때의 펌웨어 커밋 해시를 함께 적는다. 그래서 측정 전에 커밋한다.
- **갱신 시점:** 기능 단계(브랜치)마다 코드와 함께 갱신한다.
  - 개발 기록: 현재 상태, 개발 과정, 마지막 갱신(날짜·브랜치·커밋)
  - 가이드: 사용법이 바뀐 경우
  - 검증: 그 단계의 검증 방법과 결과
- **커밋:** 관련 코드와 같은 기능 브랜치에 함께 커밋한다.

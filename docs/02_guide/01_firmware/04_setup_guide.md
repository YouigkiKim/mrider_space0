# 개발 환경 설정 가이드 — 새 PC에서 Teensy 펌웨어를 올리기까지

새 PC(Windows + WSL2)에 Teensy 펌웨어 개발 환경을 처음부터 갖추는 순서다.
각 단계마다 **명령**, **확인 방법(기대 출력)**, **왜 필요한가**를 적었다.

- **대상 독자:** 이 저장소의 펌웨어를 처음 빌드·업로드하는 팀원, 새 PC로 옮기는 사람
- **한 번만 한다.** 설치가 끝난 뒤 매일 쓰는 조작(연결, 업로드, 모니터, agent)은
  [Teensy 가이드](01_teensy_guide.md) §7.1에 있다.
- **고정한 버전과 이 PC에서 확인한 버전**은 [펌웨어 개발 문서](../../01_development/01_firmware/01_firmware_development.md) §3에 있다.
  이 문서는 버전 값을 반복하지 않는다.
- **원본:** `docs/build/04-firmware.md` §4.2(PlatformIO, micro-ROS agent), `docs/build/05-software.md` §5.2(ROS 2 패키지)·§5.4(agent).
  원본은 Ubuntu PC를 가정한다. 팀은 Windows + WSL2를 쓰므로 1·2단계(WSL, usbipd)와 6단계(udev 규칙)를 더했다(15절).
- **마지막 확인:** 2026-11-27, 브랜치 `firmware/steering`
- **경로 표기:** 저장소 안 경로는 저장소 루트 기준이다. `~/uros_ws`, `~/.platformio`처럼 저장소 밖 경로는 공식 문서나
  도구의 기본 설치 위치이며, 그때마다 출처를 적었다.

---

## 0. 전체 그림과 순서

```
Windows 11
 ├─ usbipd-win ─────────── Teensy USB를 WSL로 넘겨준다            (2단계)
 ├─ VS Code + WSL 확장 ─── 편집기와 터미널                       (3단계)
 └─ WSL2: Ubuntu 22.04                                          (1단계)
     ├─ git, 저장소 ──────── 팀 fork를 clone                      (4단계)
     ├─ PlatformIO ──────── 컴파일·업로드. Teensy 도구는 첫 빌드 때 자동 설치 (5단계)
     ├─ udev 규칙 ───────── 업로드할 권한                          (6단계)
     ├─ ROS 2 Humble ────── 노트북 쪽 ROS                          (8단계)
     ├─ micro-ROS agent ─── 노트북 ↔ Teensy 다리                  (9단계)
     └─ Docker ──────────── micro-ROS 라이브러리 빌드               (10단계)
```

| 단계 | 하는 일 | bench 스케치만 쓸 때 | 본 펌웨어(`mitt_dbw`)까지 쓸 때 |
|---|---|---|---|
| 1 | WSL2와 Ubuntu 22.04 | 필요 | 필요 |
| 2 | usbipd-win (Windows) | 필요 | 필요 |
| 3 | VS Code | 권장 | 권장 |
| 4 | 기본 패키지, 저장소, git 설정 | 필요 | 필요 |
| 5 | PlatformIO | 필요 | 필요 |
| 6 | Teensy udev 규칙 | 필요 | 필요 |
| 7 | **확인 1:** bench 스케치 업로드 | **여기까지** | 필요 |
| 8 | ROS 2 Humble | — | 필요 |
| 9 | micro-ROS agent | — | 필요 |
| 10 | Docker, micro-ROS 라이브러리 | — | 필요 |
| 11 | **확인 2:** `uros_echo` + agent | — | **여기까지** |
| 12 | 문서 도구 | 문서를 고칠 때 | 문서를 고칠 때 |

- **명령을 어디에 치는지**를 단계마다 적었다.
  - **PowerShell**: Windows 시작 메뉴의 PowerShell. "(관리자)"는 마우스 오른쪽 → 관리자 권한으로 실행.
  - **WSL**: Ubuntu 터미널 또는 VS Code 터미널(프롬프트가 `사용자이름@컴퓨터이름:…$`).

---

## 1. WSL2와 Ubuntu 22.04 (Windows)

**왜:** ROS 2 Humble은 Ubuntu 22.04용으로 배포된다(ROS 2 Humble 설치 문서). 원본 문서의 명령도 모두 Ubuntu 기준이다.

**PowerShell (관리자)**
```powershell
wsl --install -d Ubuntu-22.04
```
- 끝나면 PC를 다시 시작하고, 열리는 Ubuntu 창에서 사용자 이름과 암호를 정한다.

**systemd가 켜져 있는지 확인 (WSL)**
```bash
ps -p 1 -o comm=          # 기대: systemd
```
- `systemd`가 아니면 `/etc/wsl.conf`에 아래 두 줄을 넣고, PowerShell에서 `wsl --shutdown` 뒤 Ubuntu를 다시 연다.
  ```ini
  [boot]
  systemd=true
  ```
- **왜:** 6단계의 udev 규칙은 systemd가 띄우는 `systemd-udevd`가 적용하고, 10단계의 Docker도 systemd 서비스로 돈다.

**확인**

| 명령 | 어디서 | 기대 |
|---|---|---|
| `wsl -l -v` | PowerShell | `Ubuntu-22.04 … VERSION 2` |
| `head -1 /etc/os-release` | WSL | `PRETTY_NAME="Ubuntu 22.04.x LTS"` |

---

## 2. usbipd-win — Teensy를 WSL에 연결 (Windows)

**왜:** WSL은 USB 장치를 직접 보지 못한다. Windows의 usbipd-win이 USB 장치를 WSL로 넘겨준다
(Microsoft Learn "Connect USB devices" 문서). 개념은 [Teensy 가이드](01_teensy_guide.md) §2.2에 있다.

**설치 (PowerShell)**
```powershell
winget install --interactive --exact dorssel.usbipd-win
```
- 기본 설치 위치는 `C:\Program Files\usbipd-win\`이다. WSL에서는 `/mnt/c/Program Files/usbipd-win/usbipd.exe`로 보인다.
- 확인: PowerShell을 새로 열고 `usbipd --version` → 버전이 나오면 된다.

**공유 허용 (bind) — 장치마다 처음 한 번**
1. Teensy를 USB로 꽂는다. 신호 기판에 꽂혀 있으면 로직 전원도 켠다(아래 주의).
2. PowerShell에서 `usbipd list` → `16c0:0483`(USB Serial) 줄의 **BUSID**(예: `2-3`)를 확인한다.
3. **PowerShell (관리자)**: `usbipd bind --busid 2-3`
4. Teensy의 **PROGRAM 버튼**을 눌러 program 모드로 바꾸고, `usbipd list`에 `16c0:0478`이 보이면 같은 방법으로 bind한다.
   - 실행 모드와 program 모드는 USB ID가 달라 **다른 장치로 취급**된다. 둘 다 bind해야 업로드할 때 끊기지 않는다.
   - 업로드하면 Teensy가 실행 모드로 돌아온다.
- **다른 USB 포트에 꽂으면 BUSID가 바뀐다.** 그 번호로 bind부터 다시 한다.

**연결 (attach) — 작업할 때마다 (WSL)**
```bash
"/mnt/c/Program Files/usbipd-win/usbipd.exe" attach --wsl --busid 2-3 --auto-attach
```
- 이 터미널은 **켜 둔 채로** 작업한다. Teensy가 재부팅하거나 program 모드로 바뀔 때마다 다시 붙여 준다.
- 확인: 다른 WSL 터미널에서 `lsusb | grep 16c0` → `16c0:0483 … Teensyduino Serial`.
- 시작할 때 Teensy가 꽂혀 있지 않으면 `--auto-attach`가 바로 끝난다. Teensy가 `usbipd list`에 보일 때 실행한다.

> [!WARNING]
> **신호 기판에 꽂은 Teensy는 USB만으로 켜지지 않는다.** 기판을 만들 때 `VUSB`–`VIN` 패드를 잘랐기 때문이다
> (`docs/build/04-firmware.md` 첫머리의 CAUTION). 로직 전원(UBEC A → `VIN`)을 켠 뒤 USB를 꽂는다.
> 꽂아도 `usbipd list`에 아무것도 안 나오면 고장보다 전원 없음을 먼저 의심한다.

---

## 3. VS Code (Windows, 권장)

**왜:** Windows 쪽 편집기로 WSL 안의 파일을 열고, 같은 창에서 WSL 터미널을 쓴다. [Teensy 가이드](01_teensy_guide.md) §7.1이 이 환경을 가정한다.

1. Windows에 VS Code를 설치하고, 확장(Extensions)에서 Microsoft의 **WSL** 확장을 설치한다.
2. 4단계에서 저장소를 받은 뒤, WSL 터미널의 저장소 폴더에서 `code .`를 실행한다.
3. 확인: 창 왼쪽 아래에 `WSL: Ubuntu-22.04`가 보이고, `` Ctrl+` ``로 연 터미널이 WSL 프롬프트다.

- PlatformIO IDE 확장은 **설치하지 않아도 된다.** 이 저장소는 터미널의 `pio` 명령을 쓴다(5단계).

---

## 4. 기본 패키지, 저장소, git 설정 (WSL)

**기본 패키지**
```bash
sudo apt update
sudo apt install -y git curl build-essential python3-pip python3-venv rsync
```

| 패키지 | 쓰는 곳 |
|---|---|
| `git`, `curl` | 저장소 받기, udev 규칙 내려받기(6단계) |
| `build-essential` | PC 단위 테스트의 `g++`(`firmware/mitt_dbw/test/host/run_host_tests.sh`) |
| `python3-pip`, `python3-venv` | PlatformIO 설치(5단계) |
| `rsync` | micro-ROS 라이브러리 빌드 스크립트(10단계) |

**저장소 받기** — WSL 홈 폴더 아래에 받는다.
```bash
cd ~
git clone https://github.com/YouigkiKim/mrider_space0.git
cd mrider_space0
```
- `/mnt/c/…`(Windows 드라이브) 아래에 받지 않는다. WSL에서 Windows 파일 시스템을 거치면 빌드가 크게 느려지고
  실행 권한이 꼬인다.

**원격 저장소** — `origin` = 팀 저장소, `upstream` = 교수님 저장소(읽기 전용).
```bash
git remote add upstream https://github.com/jrkwon/mrider.git
git remote set-url --push upstream no_push       # 교수님 저장소로 실수로 push하지 않게
git remote -v
```
- 기대 출력: `origin`은 fetch·push 모두 팀 저장소, `upstream`은 fetch가 `jrkwon/mrider`이고 push가 `no_push`.
- 브랜치 규칙은 [펌웨어 개발 문서](../../01_development/01_firmware/01_firmware_development.md) §8에 있다.

**커밋 저자** — GitHub 계정과 같은 이름·이메일로 설정한다.
```bash
git config --global user.name  "GitHub 사용자 이름"
git config --global user.email "GitHub 계정에 등록한 이메일"
git config user.email          # 확인: 위에서 넣은 이메일
```
- **왜:** 이메일이 GitHub 계정과 한 글자라도 다르면 커밋이 내 계정과 연결되지 않는다.
  2026-11-24에 전역 설정의 이메일 오타 때문에 커밋 4개의 저자가 잘못 기록되어, 히스토리를 다시 써야 했다.
- push 인증(GitHub 로그인)은 각자의 GitHub 설정(개인 액세스 토큰 또는 SSH 키)을 따른다.

---

## 5. PlatformIO (WSL)

**왜:** Teensy용 컴파일러, Teensy 코어 라이브러리, 업로더, 시리얼 모니터를 버전을 고정해 받아 주는 빌드 도구다.
개념은 [Teensy 가이드](01_teensy_guide.md) §7.7에 있다.

**설치** (`docs/build/04-firmware.md` §4.2, CI와 같은 방법)
```bash
pip install --user platformio
```
- `pio` 명령은 `~/.local/bin`(pip `--user` 설치 위치)에 생긴다. Ubuntu는 로그인할 때 이 폴더가 있으면
  PATH에 넣으므로(`~/.profile`), **터미널을 새로 열어야** `pio`가 보인다. 그래도 안 보이면 `source ~/.profile`.

**확인**
```bash
pio --version                  # 기대: PlatformIO Core, version 6.x
which -a pio                   # 기대: ~/.local/bin/pio (같은 경로가 두 번 나와도 괜찮다)
```
- `which -a pio`에 **서로 다른 경로**가 나오면 PlatformIO가 두 가지 방법으로 설치된 것이다. 하나를 지운다(15절의 설치 방법 차이 참고).
  같은 경로가 두 번 나오는 것은 PATH에 그 폴더가 두 번 들어 있을 뿐이라 문제없다.

**Teensy 플랫폼은 따로 설치하지 않는다.**
- 각 프로젝트의 `platformio.ini`가 `platform = teensy@6.0.0`으로 버전을 고정해 두었다.
- 첫 `pio run` 때 PlatformIO가 그 버전의 플랫폼, Teensy 코어, ARM 컴파일러를 `~/.platformio/`(PlatformIO 기본 위치)에
  받는다. `lib_deps`에 적힌 라이브러리(워치독 `WDT_T4`, 커밋 고정)도 이때 받는다. 인터넷이 필요하고 처음 한 번은 몇 분 걸린다.
- 업로드는 명령줄 업로더(`upload_protocol = teensy-cli`)를 쓴다. 기본값(`teensy-gui`)은 PJRC의 GUI 프로그램이 필요해 WSL에서 쓸 수 없다
  (`firmware/bench/platformio.ini` 주석).

---

## 6. Teensy udev 규칙 (WSL)

**왜:** 리눅스에서 USB 장치 파일은 기본적으로 root만 쓸 수 있다. 업로더는 Teensy 부트로더(program 모드)에 직접
써야 하므로 권한이 없으면 업로드가 실패한다. PJRC가 이 권한을 여는 규칙 파일(`00-teensy.rules`)을 배포하고,
설치 위치(`/etc/udev/rules.d/`)는 그 파일의 머리 주석에 적혀 있다. 두 `platformio.ini`의 주석도 이 파일을 요구한다.

```bash
curl -fsSL https://www.pjrc.com/teensy/00-teensy.rules | sudo tee /etc/udev/rules.d/00-teensy.rules > /dev/null
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**확인** (Teensy를 2단계처럼 attach한 상태)
```bash
ls -l /dev/ttyACM0             # 기대: crw-rw-rw- … (모두 읽기·쓰기)
```
- `crw-rw----`처럼 다른 사용자 권한이 없으면 규칙이 적용되지 않은 것이다. 1단계의 systemd를 확인하고, Teensy를 다시 꽂는다.
- 차량 노트북에서 쓸 고정 이름(`/dev/mitt_dbw`)은 별도 규칙이다(`docs/build/05-software.md` §5.6). Teensy 시리얼 번호가
  필요하므로 차량 통합 단계에서 만든다. 지금 문서와 명령은 `/dev/ttyACM0`을 쓴다.

---

## 7. 확인 1 — bench 스케치 올리기

여기까지 되면 `firmware/bench`의 bench 스케치를 모두 쓸 수 있다.

- 이 확인에는 `ibus_monitor`를 쓴다. 핀 15(수신기 입력)를 **읽기만** 하고 출력 핀을 움직이지 않는다.
  그래서 무엇이 배선되어 있든 안전하다.

1. 2단계의 attach 터미널을 켜 둔다.
2. 다른 WSL 터미널에서:
   ```bash
   cd firmware/bench                      # 저장소 루트에서
   pio run -e ibus_monitor -t upload
   ```
   - 처음에는 5단계의 플랫폼 다운로드 때문에 몇 분 걸린다.
   - 마지막에 `[SUCCESS]`가 나오면 성공이다. 첫 시도가 `[FAILED]`면 **같은 명령을 한 번 더** 실행한다
     (program 모드로 바뀌는 순간 WSL 연결이 잠깐 끊긴다. [Teensy 가이드](01_teensy_guide.md) §7.1).
3. 2~3초 뒤 `pio device monitor`
   - 기대 출력: `MRider bench -- i-BUS monitor (Serial3 RX = pin 15, 115200 8N1)`과
     `NO FRAMES YET -- check bind, iBUS servo port, level, ground` 반복.
     수신기가 없거나 송신기가 꺼져 있으면 이것이 정상이다.
   - 끝낼 때는 `Ctrl+C`.

---

## 8. ROS 2 Humble (WSL)

**왜:** 본 펌웨어(`mitt_dbw`)는 시리얼 모니터 대신 ROS 2 토픽으로 노트북과 대화한다.

1. **ROS 2 Humble 공식 설치 문서(Ubuntu, deb 패키지)**의 순서대로 설치한다: <https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html>
   - 패키지: `ros-humble-desktop`(RViz·rqt 도구 포함)과 `ros-dev-tools`(`colcon`, `rosdep` 등 빌드 도구)
   - 저장소 설정 방법은 공식 문서가 바뀔 수 있으므로 여기에 옮겨 적지 않는다.
2. rosdep 초기화 (처음 한 번):
   ```bash
   sudo rosdep init
   rosdep update
   ```
3. 시뮬레이터(Gazebo)·내비게이션 패키지는 펌웨어에는 필요 없다. 필요하면 `docs/build/05-software.md` §5.2–5.3을 따른다.

**확인**
```bash
source /opt/ros/humble/setup.bash
printenv ROS_DISTRO            # 기대: humble
which colcon rosdep            # 기대: /usr/bin/colcon, /usr/bin/rosdep
```
- `source /opt/ros/humble/setup.bash`는 **새 터미널마다** 필요하다([Teensy 가이드](01_teensy_guide.md) §7.7).

---

## 9. micro-ROS agent (WSL)

**왜:** Teensy의 micro-ROS는 혼자서 ROS 2 네트워크에 참여하지 못하고, 노트북의 agent가 USB 시리얼 너머의 Teensy를
ROS 2에 이어 준다. agent는 Humble apt 저장소에 없어서 **소스로 빌드**한다(`docs/build/05-software.md` §5.4).

원본 명령 그대로 (`docs/build/04-firmware.md` §4.2). 설치 위치 `~/uros_ws`는 원본이 정한 위치다.
```bash
source /opt/ros/humble/setup.bash
mkdir -p ~/uros_ws/src && cd ~/uros_ws
git clone -b humble https://github.com/micro-ROS/micro_ros_setup.git src/micro_ros_setup
rosdep install --from-paths src --ignore-src -y
colcon build && source install/local_setup.bash
ros2 run micro_ros_setup create_agent_ws.sh
ros2 run micro_ros_setup build_agent.sh && source install/local_setup.bash
```

**확인**
```bash
source /opt/ros/humble/setup.bash && source ~/uros_ws/install/local_setup.bash
ros2 pkg prefix micro_ros_agent        # 기대: …/uros_ws/install/micro_ros_agent
git -C ~/uros_ws/src/micro_ros_setup log --oneline -1   # 빌드한 커밋. 개발 문서 §3과 비교
```

---

## 10. Docker와 micro-ROS 라이브러리 (WSL)

**왜:** 펌웨어가 쓰는 micro-ROS 라이브러리 배포본(`micro_ros_arduino v2.0.8-humble`)에는 우리 메시지(`mitt_msgs`)가 없다.
그래서 공식 Docker 빌더로 `mitt_msgs`를 넣어 다시 빌드한다. 결과물(`firmware/mitt_dbw/lib/`)은 빌드 산출물이라 git에
없으므로 **PC마다 한 번** 만든다. 결정 이유는 [펌웨어 개발 문서](../../01_development/01_firmware/01_firmware_development.md) §3에 있다.

**Docker 설치** (Ubuntu의 `docker.io` 패키지. Docker Desktop은 필요 없다)
```bash
sudo apt install -y docker.io
sudo usermod -aG docker $USER          # sudo 없이 docker를 쓰도록 docker 그룹에 추가
```
- 그룹 추가는 **다시 로그인해야** 적용된다. PowerShell에서 `wsl --shutdown` 뒤 Ubuntu를 다시 연다.
- 확인: `docker run --rm hello-world` → `Hello from Docker!`

**라이브러리 빌드** (인터넷 필요, 약 5분)
```bash
cd firmware/mitt_dbw                   # 저장소 루트에서
./scripts/build_microros_lib.sh
cat lib/micro_ros_arduino/BUILD_INFO.txt
```
- 기대: 첫 줄이 `micro_ros_arduino v2.0.8-humble @ 8d527c4…, target teensy4`. 나머지 줄에 빌더 이미지, 넣은 `mitt_msgs`의 커밋이 기록된다.
- **다시 빌드할 때:** `ros2_ws/src/mitt_msgs`나 `firmware/mitt_dbw/microros/colcon.meta`가 바뀌었을 때. 메시지를 바꾸면
  노트북 쪽 `colcon build`도 함께 다시 한다(11단계 (1)).

---

## 11. 확인 2 — 노트북과 Teensy가 ROS 2로 대화하는가

여기까지 되면 본 펌웨어(`mitt_dbw`)를 다룰 수 있다. 이 확인은 `uros_echo`를 쓴다.
`uros_echo`는 **핀을 하나도 쓰지 않는** 통신 시험 펌웨어로, "도구·agent·메시지 빌드 문제"와 "DBW 펌웨어 문제"를
나누어 본다(`firmware/mitt_dbw/src/uros_echo.cpp` 머리 주석).

**(1) 노트북 쪽 `mitt_msgs`** (저장소 루트에서)
```bash
cd ros2_ws && source /opt/ros/humble/setup.bash && colcon build --packages-select mitt_msgs
```
- 기대: `Summary: 1 package finished`

**(2) PC 단위 테스트** (Teensy 불필요)
```bash
cd firmware/mitt_dbw && ./test/host/run_host_tests.sh
```
- 기대: `N passed, 0 failed`

**(3) `uros_echo` + agent**
1. 시리얼 모니터가 켜져 있으면 끈다. 포트는 한 번에 한 프로그램만 쓸 수 있다.
2. 업로드 (`firmware/mitt_dbw`에서): `pio run -e uros_echo -t upload` (첫 시도가 실패하면 한 번 더)
3. **터미널 A — agent** (켜 둔다)
   ```bash
   source /opt/ros/humble/setup.bash && source ~/uros_ws/install/local_setup.bash
   ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200
   ```
   - 기대: `session established`
4. **터미널 B — 확인** (저장소 루트에서)
   ```bash
   source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash
   ros2 topic hz /mitt/dbw/status
   ```
   - 기대: 약 50 Hz
5. 끝나면 agent를 `Ctrl+C`로 끈다. 다음에 업로드할 때 포트를 비워 두기 위해서다.

다음은 [Teensy 가이드](01_teensy_guide.md) §7.3(Stage 0)부터 단계별로 진행한다.

---

## 12. 문서 도구 (선택, WSL)

`docs/` 아래 문서를 고쳐 push하기 전에 검사한다(`CLAUDE.md`).
```bash
pip install --user -r requirements-docs.txt
bash scripts/check_docs.sh             # mkdocs --strict, 깨진 앵커, 그림 최신 여부 등
```

---

## 13. 버전 기록

설치를 마치면 실제로 받은 버전을 확인한다. 고정 버전이 바뀌었으면
[펌웨어 개발 문서](../../01_development/01_firmware/01_firmware_development.md) §3의 표를 함께 고쳐 커밋한다
(`docs/design/software.md` §6.3, `docs/build/04-firmware.md` §4.2).

| 무엇 | 명령 | 어디서 |
|---|---|---|
| usbipd-win | `usbipd --version` | PowerShell |
| PlatformIO, Teensy 플랫폼 | `pio --version`, `cd firmware/mitt_dbw && pio pkg list` | WSL |
| Docker | `docker --version` | WSL |
| micro-ROS 라이브러리 | `cat firmware/mitt_dbw/lib/micro_ros_arduino/BUILD_INFO.txt` | WSL |
| micro-ROS agent | `git -C ~/uros_ws/src/micro_ros_setup log --oneline -1` | WSL |
| ROS 2 | `dpkg -l ros-humble-desktop` | WSL |

---

## 14. 막혔을 때 (설치 단계)

매일 작업 중에 생기는 문제(첫 업로드 실패, 재부팅 반복 등)는 [Teensy 가이드](01_teensy_guide.md) §7.1 (6)에 있다.

| 증상 | 원인 | 해결 |
|---|---|---|
| `pio: command not found` | 설치 직후라 `~/.local/bin`이 아직 PATH에 없음 | 터미널을 새로 연다(또는 `source ~/.profile`) |
| `usbipd list`에 Teensy가 없음 | 전원 없음(`VUSB`–`VIN` 절단), 데이터선이 아닌 충전 전용 케이블 | 로직 전원을 켠다. 업로드가 되던 케이블로 바꾼다 |
| attach할 때 장치가 공유되지 않았다는 오류 | bind를 안 함 | 2단계 bind (관리자 PowerShell). 포트를 바꿨으면 새 BUSID로 |
| attach가 `no device with busid`로 바로 끝남 | 시작할 때 Teensy가 꽂혀 있지 않음 | Teensy가 `usbipd list`에 보일 때 다시 실행 |
| 업로드가 권한 오류(`Permission denied`, 장치를 열 수 없음)로 실패 | udev 규칙이 없거나 적용 안 됨 | 6단계. systemd 확인(1단계) 후 Teensy를 다시 꽂는다 |
| `pio run`이 플랫폼을 받다가 실패 | 인터넷 연결 | 연결을 확인하고 다시 실행 |
| `micro_ros_arduino.h: No such file or directory` | micro-ROS 라이브러리를 아직 안 만듦 | 10단계 |
| `docker not usable: is your user in the docker group?` | 그룹 추가가 아직 적용 안 됨 | `wsl --shutdown` 뒤 다시 열기 |
| `rosdep install`이 초기화되지 않았다고 실패 | rosdep 초기화 안 함 | 8단계 2번 |
| `Package 'micro_ros_agent' not found` | agent 설정을 source하지 않음 | `source ~/uros_ws/install/local_setup.bash` |
| agent는 연결됐는데 `/mitt/dbw/status`를 못 읽음 | 확인 터미널이 `mitt_msgs`를 모름 | `source ros2_ws/install/setup.bash` (11단계 (1)을 먼저) |

---

## 15. 원본과 다른 점

| 항목 | 원본 | 이 문서 | 이유 |
|---|---|---|---|
| 운영체제 | Ubuntu PC 가정 | Windows + WSL2 (1·2단계 추가) | 팀 노트북이 Windows다. WSL은 USB를 직접 못 봐서 usbipd-win이 필요하다 |
| Teensy udev 규칙 | 없음. `05-software.md` §5.6은 고정 이름(`/dev/mitt_dbw`) 규칙만 | PJRC `00-teensy.rules` 추가 (6단계) | 명령줄 업로더(`teensy-cli`)가 부트로더에 쓰려면 필요하다. 두 `platformio.ini` 주석이 요구한다 |
| PlatformIO 설치 | `pip install --user platformio` | 같음 | — 다만 개발 문서 §3의 PC는 PlatformIO 공식 설치 스크립트(`get-platformio.py`)로 설치해 `~/.platformio/penv`에 있고, `~/.local/bin`에 링크가 있다. 어느 쪽이든 `pio`가 `~/.local/bin`에서 실행되면 같다. 두 가지를 함께 설치하지는 않는다 |
| micro-ROS 라이브러리 | 배포본 `micro_ros_arduino v2.0.8-humble` | 같은 버전을 Docker로 `mitt_msgs`를 넣어 다시 빌드 (10단계) | 배포본에 우리 메시지가 없다. 결정 기록은 개발 문서 §3, §7 |

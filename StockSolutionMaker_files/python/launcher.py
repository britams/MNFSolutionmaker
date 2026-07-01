# ============================================================================
# launcher.py  —  이 프로그램의 "메인" 파일 (exe를 만들 때 시작점으로 쓰는 파일)
#
# 역할: Flask로 아주 작은 웹서버를 띄우고, 브라우저를 자동으로 열어서
#       templates/index.html 화면을 보여준 뒤, 계산 요청이 오면 결과를 돌려줌.
#
# 이 파일에는 "계산 공식"이 없습니다!
#   -> 염류 목록(SALTS)과 실제 계산 함수(calculate)는 같은 폴더의 calculator.py 에 있음.
# 화면(HTML/CSS/JS)도 이 파일에는 없습니다!
#   -> frontend/templates/index.html, frontend/static/style.css, script.js 참고.
# ============================================================================

import os
import sys
import subprocess
import tempfile
import threading
import time
import webbrowser

from flask import Flask, render_template, request, jsonify  # Flask = 파이썬으로 웹서버를 만드는 라이브러리

# calculator.py 에서 정의한 것들을 가져다 씀 (이 파일은 그저 "가져다 쓰는" 입장)
#   SALTS, CONC_UNITS, VOLUME_UNITS, WATER_OUT_UNITS : 선택지 목록(딕셔너리) -> calculator.py 에 정의됨
#   calculate()                                       : 실제 계산 함수      -> calculator.py 에 정의됨
from calculator import SALTS, CONC_UNITS, VOLUME_UNITS, WATER_OUT_UNITS, calculate

PORT = 5050  # 이 포트로 웹서버가 열림 -> 브라우저 주소는 http://127.0.0.1:5050/


def resource_path(relative_path):
    """
    exe로 실행될 때와 python 스크립트로 실행될 때, html/css/js 파일을 찾는 위치가 다르기 때문에
    상황에 맞는 경로를 계산해주는 함수.
    - PyInstaller로 exe를 만들면, 실행 시 templates/static 폴더가 sys._MEIPASS 라는 임시 폴더에 풀림.
    - exe가 아니라 그냥 python launcher.py 로 실행 중이면 sys._MEIPASS 가 없으므로,
      이 파일이 있는 폴더를 기준으로 경로를 잡음.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Flask 앱(웹서버) 객체 생성.
# template_folder / static_folder 를 위 resource_path() 로 지정해서, exe로 실행돼도 html/css/js를 찾게 함.
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)


@app.route("/")  # 브라우저 주소창에 http://127.0.0.1:5050/ 로 접속하면 이 함수가 실행됨
def index():
    # frontend/templates/index.html 화면을 보여줌.
    # salts, conc_units 같은 데이터를 html로 넘겨서, 화면의 <select> 옵션들이 자동으로 채워지게 함.
    return render_template(
        "index.html",
        salts=SALTS,
        conc_units=CONC_UNITS,
        volume_units=VOLUME_UNITS,
        water_units=WATER_OUT_UNITS,
    )


@app.route("/calculate", methods=["POST"])  # 화면에서 "계산하기" 버튼을 누르면 script.js가 이 주소로 요청을 보냄
def calculate_route():
    data = request.get_json()  # 브라우저(script.js)가 JSON 형태로 보낸 입력값을 받음
    try:
        salt_key = data["salt"]
        conc_unit_key = data["conc_unit"]
        conc_value = float(data["conc_value"])
        volume_unit_key = data["volume_unit"]
        volume_value = float(data["volume_value"])
        water_unit_key = data["water_unit"]
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "입력값을 확인해주세요."}), 400  # 값이 비었거나 숫자가 아니면 에러 응답

    if salt_key not in SALTS or conc_unit_key not in CONC_UNITS or volume_unit_key not in VOLUME_UNITS or water_unit_key not in WATER_OUT_UNITS:
        return jsonify({"error": "잘못된 선택값입니다."}), 400

    # 농도/부피는 음수나 0이 되면 계산이 성립하지 않으므로 여기서 미리 막습니다.
    if conc_value <= 0 or volume_value <= 0:
        return jsonify({"error": "몰농도와 부피는 0보다 커야 합니다. (음수 입력 불가)"}), 400

    # 실제 계산은 여기서 하지 않고, calculator.py의 calculate() 함수에게 통째로 맡김 (역할 분리)
    r = calculate(salt_key, conc_unit_key, conc_value, volume_unit_key, volume_value, water_unit_key)
    return jsonify(r)  # 계산 결과를 JSON으로 다시 브라우저에 돌려줌 -> script.js가 화면에 그려줌


def find_browser():
    """
    창을 닫으면 프로그램 자체가 같이 꺼지게 하려면, 그냥 webbrowser.open()으로
    "탭"을 여는 대신 Edge/Chrome을 "--app=" 모드(주소창 없는 전용 앱 창)로 따로
    띄워야 합니다. 이 함수는 컴퓨터에 설치된 Edge/Chrome의 실제 exe 경로를 찾습니다.
    """
    program_files = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                      os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")]
    candidates = []
    for pf in program_files:
        candidates.append(os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"))
        candidates.append(os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


if __name__ == "__main__":
    # 이 파일을 직접 실행했을 때(=exe로 실행했을 때 포함)만 실행되는 부분.
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.5)  # 서버가 실제로 뜰 때까지 잠깐 대기

    url = f"http://127.0.0.1:{PORT}/"
    browser_exe = find_browser()
    if browser_exe:
        # Edge/Chrome이 이미 백그라운드로 켜져 있으면 "--app" 요청이 기존 창으로
        # 넘어가버려서, 우리가 띄운 프로세스는 바로 끝나버립니다(창을 감지 못 함).
        # 그래서 전용 임시 프로필(user-data-dir)로 완전히 "별개의" 창을 띄워서,
        # 그 창(프로세스)이 실제로 닫힐 때까지 기다릴 수 있게 합니다.
        profile_dir = os.path.join(tempfile.gettempdir(), "stocksolutionmaker_profile")
        browser_process = subprocess.Popen([
            browser_exe,
            f"--app={url}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
        ])
        browser_process.wait()
    else:
        # Edge/Chrome을 못 찾으면 그냥 기본 브라우저 탭으로 엽니다.
        # (이 경우엔 탭을 닫아도 프로그램이 자동으로 안 꺼질 수 있습니다.)
        webbrowser.open(url)
        server_thread.join()

    os._exit(0)  # 창이 닫히면 서버 스레드까지 프로그램 전체를 완전히 종료

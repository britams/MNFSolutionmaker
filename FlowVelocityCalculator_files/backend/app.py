# app.py
# ------------------------------------------------------------------
# 이 파일은 "연속방정식 유속 계산기" 웹앱의 서버(백엔드) 코드입니다.
#
# 연속방정식(Q = A x V, 부피유량 = 단면적 x 유속)을 이용해서,
# 유속(m/s, mm/s) 과 부피유량(uL/s, uL/min) 을 서로 변환해줍니다.
# 어느 쪽 값을 입력하든(둘 중 아는 값을 넣으면), 단면적(A)만 알면
# 나머지 쪽 값을 계산할 수 있습니다.
#
# 단면적(A)을 구하는 방법은 2가지 중 하나를 고를 수 있습니다.
#   1) 주사기 종류 선택 (내경 d(mm)으로부터 A = pi x (d/2)^2 계산)
#   2) 채널의 width x height 직접 입력
# ------------------------------------------------------------------

import os
import sys
import subprocess
import tempfile
import threading
import time
import webbrowser
import math
from flask import Flask, request, jsonify, send_from_directory

if getattr(sys, "frozen", False):
    FRONTEND_DIR = os.path.join(sys._MEIPASS, "frontend")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__)

# ------------------------------------------------------------------
# 주사기 종류별 내경(d, mm). 사진 속 표와 동일한 값입니다.
# 단면적 A(mm^2) = pi x (d/2)^2 로 계산합니다.
# ------------------------------------------------------------------
SYRINGES = {
    "1ml": 4.78,
    "3ml": 8.66,
    "5ml": 12.07,
    "10ml": 14.5,
    "20ml": 19.13,
    "30ml": 21.69,
    "50/60ml": 26.7,
}

# 채널 width/height 입력 단위를 mm로 통일하기 위한 환산표
LENGTH_UNIT_TO_MM = {
    "cm": 10,
    "mm": 1,
    "um": 0.001,
}

# 유속/유량 단위 목록 (입력, 출력 모두 이 4개 중에서 고를 수 있음)
FLOW_UNITS = ("m/s", "mm/s", "uL/s", "uL/min")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    연속방정식(Q = A x V)을 이용한 계산입니다.

    1) 먼저 단면적 A(mm^2)를 구합니다. (주사기 선택 또는 width x height)
    2) 입력값을 부피유량 Q(uL/s = mm^3/s) 기준으로 통일합니다.
       - 입력 단위가 유속(m/s, mm/s)이면: Q = V x A
       - 입력 단위가 유량(uL/s, uL/min)이면: 그대로/시간단위만 환산
    3) Q를 사용자가 고른 출력 단위로 다시 변환합니다.
       - 출력 단위가 유속(m/s, mm/s)이면: V = Q / A
       - 출력 단위가 유량(uL/s, uL/min)이면: 시간단위만 환산
    (1 mm^3 = 1 uL 이므로, mm과 uL 기준으로 계산하면 별도 단위 변환이 필요 없습니다.)
    """
    data = request.get_json()

    try:
        # 1) 단면적(A, mm^2) 계산
        area_mode = data["areaMode"]
        if area_mode == "syringe":
            syringe_key = data["syringe"]
            if syringe_key not in SYRINGES:
                return jsonify({"error": "주사기 종류를 올바르게 선택해주세요."}), 400
            diameter_mm = SYRINGES[syringe_key]
            area_mm2 = math.pi * (diameter_mm / 2) ** 2
        elif area_mode == "channel":
            width_value = float(data["channelWidth"])
            height_value = float(data["channelHeight"])
            length_unit = data["channelUnit"]
            if length_unit not in LENGTH_UNIT_TO_MM:
                return jsonify({"error": "채널 단위를 올바르게 선택해주세요."}), 400
            if width_value <= 0 or height_value <= 0:
                return jsonify({"error": "채널의 width와 height는 0보다 커야 합니다."}), 400
            width_mm = width_value * LENGTH_UNIT_TO_MM[length_unit]
            height_mm = height_value * LENGTH_UNIT_TO_MM[length_unit]
            area_mm2 = width_mm * height_mm
        else:
            return jsonify({"error": "단면적 계산 방식을 올바르게 선택해주세요."}), 400

        # 2) 입력값을 Q(uL/s)로 통일
        input_value = float(data["inputValue"])
        input_unit = data["inputUnit"]
        output_unit = data["outputUnit"]
        if input_unit not in FLOW_UNITS or output_unit not in FLOW_UNITS:
            return jsonify({"error": "유속/유량 단위를 올바르게 선택해주세요."}), 400
        if input_value <= 0:
            return jsonify({"error": "입력값은 0보다 커야 합니다."}), 400

        if input_unit == "m/s":
            q_uls = (input_value * 1000) * area_mm2
        elif input_unit == "mm/s":
            q_uls = input_value * area_mm2
        elif input_unit == "uL/s":
            q_uls = input_value
        else:  # "uL/min"
            q_uls = input_value / 60

        # 3) Q(uL/s)를 원하는 출력 단위로 변환
        if output_unit == "m/s":
            result_value = (q_uls / area_mm2) / 1000
        elif output_unit == "mm/s":
            result_value = q_uls / area_mm2
        elif output_unit == "uL/s":
            result_value = q_uls
        else:  # "uL/min"
            result_value = q_uls * 60

        return jsonify({
            "areaMm2": area_mm2,
            "resultValue": result_value,
            "resultUnit": output_unit,
        })

    except KeyError as e:
        return jsonify({"error": f"입력값이 누락되었습니다: {e}"}), 400
    except ValueError:
        return jsonify({"error": "숫자를 올바르게 입력해주세요."}), 400


def find_browser():
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
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.5)

    url = "http://127.0.0.1:5055/"
    browser_exe = find_browser()
    if browser_exe:
        profile_dir = os.path.join(tempfile.gettempdir(), "flowvelocitycalculator_profile")
        browser_process = subprocess.Popen([
            browser_exe,
            f"--app={url}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
        ])
        browser_process.wait()
    else:
        webbrowser.open(url)
        server_thread.join()

    os._exit(0)

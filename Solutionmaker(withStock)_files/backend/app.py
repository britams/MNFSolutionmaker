# app.py
# ------------------------------------------------------------------
# 이 파일은 "몰 농도 희석 계산기" 웹앱의 서버(백엔드) 코드입니다.
#
# [초보자를 위한 설명]
# - 우리 몸(브라우저 화면)은 frontend 폴더의 HTML/CSS/JS 가 담당하고,
# - 이 파일(app.py)은 "머리"처럼 계산을 담당합니다.
# - Flask 는 파이썬으로 아주 쉽게 웹 서버를 만들 수 있게 해주는 라이브러리입니다.
#
# 이 서버가 하는 일은 딱 2가지입니다.
#   1) 사용자가 브라우저 주소창에 접속하면 frontend 폴더의 화면(html/css/js)을 보내준다.
#   2) 사용자가 계산 버튼을 누르면(/api/calculate 로 요청이 오면) 실제 계산을 해서
#      결과를 JSON(자바스크립트가 읽기 쉬운 데이터 형식)으로 돌려준다.
# ------------------------------------------------------------------

import os            # 파일 경로 조합, 폴더 확인, 환경변수(PROGRAMFILES 등) 읽기 등 "운영체제" 관련 기능
import sys           # exe로 묶였는지(frozen) 확인하고, PyInstaller가 만든 임시 폴더(_MEIPASS) 경로를 알아낼 때 사용
import subprocess    # 파이썬 코드에서 다른 프로그램(여기서는 Edge/Chrome 브라우저)을 새 프로세스로 실행할 때 사용
import tempfile      # 브라우저 전용 임시 프로필 폴더를 만들 때, OS의 임시 폴더 경로를 가져오는 데 사용
import threading     # Flask 서버를 "별도의 스레드"에서 실행해서, 동시에 브라우저도 띄울 수 있게 해줌
import time          # 서버가 완전히 켜질 때까지 잠깐 기다리는 용도(time.sleep)
import webbrowser    # 컴퓨터의 기본 웹 브라우저로 특정 주소(url)를 열어주는 파이썬 표준 라이브러리
from flask import Flask, request, jsonify, send_from_directory
# Flask                  : 파이썬으로 웹 서버를 만들게 해주는 핵심 라이브러리 (이 앱의 "서버 몸통")
# request                : 브라우저(프론트엔드)가 보낸 요청 데이터(JSON 등)를 읽을 때 사용
# jsonify                : 파이썬 딕셔너리(dict)를 JSON 형식으로 바꿔서 브라우저에 응답으로 보낼 때 사용
# send_from_directory    : frontend 폴더 안의 html/css/js 같은 "파일 그대로"를 응답으로 보낼 때 사용

# exe로 묶였을 때는(PyInstaller) frontend 파일들이 sys._MEIPASS라는 임시 폴더 안에 들어있고,
# 그냥 python app.py로 실행할 때는 backend 옆의 frontend 폴더를 그대로 사용합니다.
if getattr(sys, "frozen", False):
    FRONTEND_DIR = os.path.join(sys._MEIPASS, "frontend")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__)

# ------------------------------------------------------------------
# 기준 상태: 대기압(1 atm), 섭씨 20도(20°C)
# 아래 SALTS(몰질량/밀도)와 WATER_DENSITY 값은
# 바탕화면\MNFSolutionmaker\python\calculator.py 에서 쓰던 값과 "동일한 조건"으로 그대로 가져온 값입니다.
# (몰질량은 IUPAC 표준 원자량 기준, 밀도는 CRC Handbook 기준 20°C 값)
# ------------------------------------------------------------------
WATER_DENSITY = 0.998207  # 증류수 밀도 (g/mL, 20°C, 1 atm)

# 제조/희석에 사용할 염류 목록. molar_mass(g/mol)와 density(g/mL)는 "고체 상태" 염류의 값입니다.
# -> g 단위 변환(부피 <-> 질량)을 할 때, 녹아있는 염류가 실제로 차지하는 부피를 계산하는 데 사용됩니다.
# 1 cm³ = 1 mL
SALTS = {
    "NaCl":    {"molar_mass": 58.442769,  "density": 2.165000},
    "Na2SO4":  {"molar_mass": 142.042138, "density": 2.664000},
    "KCl":     {"molar_mass": 74.551300,  "density": 1.984000},
    "K2SO4":   {"molar_mass": 174.259200, "density": 2.662000},
    "LiCl":    {"molar_mass": 42.394000,  "density": 2.068000},
    "Li2SO4":  {"molar_mass": 109.944600, "density": 2.221000},
    "H2Li2O5S":{"molar_mass": 127.96, "density": 2.06},
}

# ------------------------------------------------------------------
# 단위 변환표
# 사용자가 mM, uM, nM 처럼 다양한 단위로 값을 입력해도
# 계산할 때는 전부 "M(몰농도)" 과 "L(리터)" 기준으로 통일해야 계산이 쉬워집니다.
# 예) 10 mM = 10 * 0.001 M = 0.01 M
# ------------------------------------------------------------------
CONC_UNIT_TO_M = {
    "M": 1,
    "mM": 1e-3,
    "uM": 1e-6,
    "nM": 1e-9,
}

VOLUME_UNIT_TO_L = {
    "L": 1,
    "mL": 1e-3,
    "uL": 1e-6,
}

# 결과(필요한 stock 양 / 필요한 증류수 양)를 표시할 때 고를 수 있는 단위: L, mL, g 세 가지.
# (g 단위는 아래 액체를 "질량"으로 나타낸 값이며, 계산 시 SALTS 밀도/몰질량과 WATER_DENSITY가 사용됩니다.)
RESULT_UNITS = ("L", "mL", "g")


@app.route("/")
def index():
    """
    브라우저 주소창에 http://127.0.0.1:5001 만 입력하고 접속했을 때
    frontend/index.html 파일을 찾아서 보내줍니다.
    """
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """
    index.html이 필요로 하는 style.css, script.js 같은 부속 파일들을
    요청받으면 frontend 폴더에서 찾아 보내줍니다.
    (예: /style.css 요청 -> frontend/style.css 파일 전송)
    """
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    실제 희석 계산을 하는 부분입니다.

    화면에서 입력받는 값 (이미지 속 기호와 대응):
        salt            -> 만들려는 염류 (NaCl, KCl 등) : g 단위 변환에 사용
        stockConc       -> x : stock solution 몰 농도
        workingConc     -> y : 만들고 싶은 working solution 몰 농도
        workingVolume   -> z : 만들고 싶은 working solution 부피
        결과 1          -> N : 필요한 stock solution 양 (L/mL/g 중 선택)
        결과 2          -> W : 필요한 증류수 양 (L/mL/g 중 선택)

    공식 (희석 공식 C1V1 = C2V2 를 그대로 적용):
        x * N = y * z
        =>  N = (y * z) / x               ... 필요한 stock 부피
        =>  W = z - N                     ... 필요한 증류수 부피
        (전체 부피 z 중에서 stock으로 채우고 남는 만큼을 증류수로 채우면 되기 때문입니다.
         희석 전후로 녹아있는 소금의 양은 그대로이므로, 소금이 차지하는 부피는
         이 뺄셈에서 서로 정확히 상쇄됩니다 - 그래서 아래처럼 간단히 계산해도 정확합니다.)
    """
    data = request.get_json()

    try:
        # 0) 선택한 염류 정보를 가져옵니다. (g 단위 변환에만 사용)
        salt_key = data["salt"]
        if salt_key not in SALTS:
            return jsonify({"error": "염류를 올바르게 선택해주세요."}), 400
        salt = SALTS[salt_key]

        # 1) stock 농도를 입력값 그대로 읽고, 단위를 M(몰농도)로 통일합니다.
        stock_value = float(data["stockConc"])
        stock_unit = data["stockConcUnit"]
        x = stock_value * CONC_UNIT_TO_M[stock_unit]

        # 2) working solution 농도를 읽고 M로 통일합니다.
        working_value = float(data["workingConc"])
        working_unit = data["workingConcUnit"]
        y = working_value * CONC_UNIT_TO_M[working_unit]

        # 3) 만들고 싶은 working solution의 부피를 읽고 L로 통일합니다.
        volume_value = float(data["workingVolume"])
        volume_unit = data["workingVolumeUnit"]
        z = volume_value * VOLUME_UNIT_TO_L[volume_unit]

        # 4) 결과를 어떤 단위(L/mL/g)로 보고 싶은지 읽습니다.
        stock_out_unit = data["stockOutUnit"]
        water_out_unit = data["waterOutUnit"]
        if stock_out_unit not in RESULT_UNITS or water_out_unit not in RESULT_UNITS:
            return jsonify({"error": "결과 단위는 L, mL, g 중에서 선택해주세요."}), 400

        # 5) 값 검증 (말이 안 되는 입력은 미리 걸러줍니다)
        if x <= 0:
            return jsonify({"error": "stock 농도는 0보다 커야 합니다."}), 400
        if y <= 0 or z <= 0:
            return jsonify({"error": "working 농도와 부피는 0보다 커야 합니다."}), 400
        if y > x:
            # 희석(진한 용액 -> 묽은 용액)만 가능하므로,
            # working 농도가 stock 농도보다 클 수는 없습니다.
            return jsonify({
                "error": "working 농도가 stock 농도보다 높을 수 없습니다. (희석만 가능합니다)"
            }), 400

        # 6) 핵심 계산 (전부 mL 단위로 계산해서 헷갈리지 않게 합니다)
        z_ml = z * 1000
        needed_stock_ml = (y * z) / x * 1000       # N : 필요한 stock 부피(mL)
        needed_water_ml = z_ml - needed_stock_ml    # W : 필요한 증류수 부피(mL)

        if needed_water_ml < 0:
            # 이론상 x>=y 조건에서는 항상 0 이상이지만, 혹시 모를 부동소수점 오차를 방지합니다.
            needed_water_ml = 0

        # 7) 결과를 사용자가 고른 단위(L/mL/g)로 변환합니다.
        stock_display = to_display_unit(needed_stock_ml, stock_out_unit, x, salt)
        water_display = to_display_unit(needed_water_ml, water_out_unit, None, None)

        return jsonify({
            "saltName": salt_key,
            "neededStockMl": needed_stock_ml,
            "neededWaterMl": needed_water_ml,
            "stockDisplayValue": round(stock_display, 4),
            "stockDisplayUnit": stock_out_unit,
            "waterDisplayValue": round(water_display, 4),
            "waterDisplayUnit": water_out_unit,
        })

    except KeyError as e:
        # 필요한 값이 하나라도 안 왔을 때
        return jsonify({"error": f"입력값이 누락되었습니다: {e}"}), 400
    except ValueError:
        # 숫자가 아닌 값이 들어왔을 때 (예: 빈칸, 문자)
        return jsonify({"error": "숫자를 올바르게 입력해주세요."}), 400


def to_display_unit(volume_ml, unit, molarity, salt):
    """
    부피(mL)를 원하는 단위(L / mL / g)로 바꿔주는 함수입니다.

    - L, mL 로 바꾸는 것은 단순한 단위 환산이라 salt 정보가 필요 없습니다.
    - g(질량)로 바꾸려면 "이 액체 안에 무엇이 녹아 있는지"를 알아야 합니다.
        molarity 와 salt 가 주어지면(=녹아있는 용액인 경우):
            녹아있는 소금 질량(g)      = molarity(M) * 부피(L) * 몰질량(g/mol)
            그 소금이 차지하는 부피(mL) = 소금 질량 / 소금 밀도(g/mL)
            나머지는 순수한 물이므로     물 부피(mL) * 물 밀도(g/mL) 만큼의 질량을 더합니다.
        molarity 와 salt 가 없으면(=순수 증류수인 경우):
            그냥 부피(mL) * 물 밀도(g/mL) 로 질량을 구합니다.
    """
    if unit == "L":
        return volume_ml / 1000
    if unit == "mL":
        return volume_ml

    # 여기부터는 unit == "g" 인 경우
    if molarity is not None and salt is not None:
        volume_l = volume_ml / 1000
        salt_mass_g = molarity * volume_l * salt["molar_mass"]     # 녹아있는 소금의 질량
        salt_volume_ml = salt_mass_g / salt["density"]              # 그 소금이 차지하는 부피
        water_volume_ml = volume_ml - salt_volume_ml                # 나머지는 순수한 물의 부피
        water_mass_g = water_volume_ml * WATER_DENSITY
        return salt_mass_g + water_mass_g

    # 순수 증류수는 전부 물이므로 물 밀도만 곱하면 됩니다.
    return volume_ml * WATER_DENSITY


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
    # 이 파일을 파이썬으로 직접 실행하면(=exe로 실행해도) 서버가 켜집니다.
    # 기본 주소: http://127.0.0.1:5001
    # debug=False : 실행파일(더블클릭)로 켤 때는 터미널 창이 없으므로,
    #               콘솔이 필요한 디버그 자동재시작 기능은 꺼둡니다.
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.5)  # 서버가 실제로 뜰 때까지 잠깐 대기

    url = "http://127.0.0.1:5001/"
    browser_exe = find_browser()
    if browser_exe:
        # Edge/Chrome이 이미 백그라운드로 켜져 있으면 "--app" 요청이 기존 창으로
        # 넘어가버려서, 우리가 띄운 프로세스는 바로 끝나버립니다(창을 감지 못 함).
        # 그래서 전용 임시 프로필(user-data-dir)로 완전히 "별개의" 창을 띄워서,
        # 그 창(프로세스)이 실제로 닫힐 때까지 기다릴 수 있게 합니다.
        profile_dir = os.path.join(tempfile.gettempdir(), "solutionmaker_withstock_profile")
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

# ============================================================================
# calculator.py  —  실제 "계산 로직"이 들어있는 파일.
#
# launcher.py(메인)가 여기 있는 데이터(SALTS 등)와 calculate() 함수를 가져다 씀.
# 화면(HTML/JS)이나 웹서버(launcher.py)는 "계산이 어떻게 되는지" 몰라도 되도록,
# 계산이라는 기능만 이 파일 하나로 따로 떼어놓은 것 (이렇게 나눠두면 나중에 계산 공식만
# 수정하고 싶을 때 이 파일만 고치면 됨).
# ============================================================================

# 기준 상태: 대기압(1 atm), 섭씨 20도(20°C)
# 몰질량(g/mol)은 IUPAC 표준 원자량 기준, 밀도(g/mL)는 CRC Handbook 기준(20°C) 값을 사용함
WATER_DENSITY = 0.998207  # 증류수 밀도 (g/mL, 20°C, 1 atm)

# 제조 가능한 염류 목록 (딕셔너리 안에 딕셔너리).
# key("1", "2", ...)는 화면의 <select> 옵션 값과 그대로 매칭됨 (frontend/templates/index.html 참고)
SALTS = {
    "1": {"name": "NaCl", "molar_mass": 58.442769, "density": 2.165000},
    "2": {"name": "Na2SO4", "molar_mass": 142.042138, "density": 2.664000},
    "3": {"name": "KCl", "molar_mass": 74.551300, "density": 1.984000},
    "4": {"name": "K2SO4", "molar_mass": 174.259200, "density": 2.662000},
    "5": {"name": "LiCl", "molar_mass": 42.394000, "density": 2.068000},
    "6": {"name": "Li2SO4", "molar_mass": 109.944600, "density": 2.221000},
}

# 농도/부피 단위 변환표.
# "to_molar"/"to_liter" 값을 곱하면 표준 단위(M, L)로 바뀌도록 만든 계수임
# 예) mM(밀리몰) 입력값 * 0.001 = M(몰) 값
CONC_UNITS = {"1": {"label": "M (mol/L)", "to_molar": 1.0}, "2": {"label": "mM (mmol/L)", "to_molar": 0.001}}
VOLUME_UNITS = {"1": {"label": "L", "to_liter": 1.0}, "2": {"label": "mL", "to_liter": 0.001}}
WATER_OUT_UNITS = {"1": "L", "2": "mL", "3": "g"}


def calculate(salt_key, conc_unit_key, conc_value, volume_unit_key, volume_value, water_unit_key):
    """
    이 프로그램의 핵심 함수 (실제 계산은 전부 여기서 일어남).

    입력: 선택한 염류 key, 농도단위 key, 농도 값, 부피단위 key, 부피 값, 증류수 출력단위 key
          (key들은 위 SALTS/CONC_UNITS/VOLUME_UNITS/WATER_OUT_UNITS 딕셔너리의 "1", "2" 같은 문자열)
    출력: 결과 값들을 담은 딕셔너리
          -> launcher.py 의 calculate_route() 가 이 딕셔너리를 그대로 JSON으로 브라우저에 전달함
    """
    salt = SALTS[salt_key]
    conc_unit = CONC_UNITS[conc_unit_key]
    volume_unit = VOLUME_UNITS[volume_unit_key]
    water_unit = WATER_OUT_UNITS[water_unit_key]

    # 사용자가 입력한 값을 표준 단위(몰농도 M, 부피 L)로 환산
    molarity = conc_value * conc_unit["to_molar"]
    volume_l = volume_value * volume_unit["to_liter"]
    volume_ml = volume_l * 1000

    # 몰농도 공식: 몰수(mol) = 몰농도(M) x 부피(L)  ->  질량(g) = 몰수 x 몰질량(g/mol)
    needed_mass = molarity * volume_l * salt["molar_mass"]

    # 질량(g)을 밀도(g/mL)로 나누면, 그 염류가 고체 상태에서 실제로 차지하는 부피(mL)가 나옴
    # (용질이 녹으면서 차지하는 부피만큼, 넣어야 할 증류수 양을 보정하기 위함)
    solute_volume_ml = needed_mass / salt["density"]

    # 전체 목표 부피에서 염류가 차지하는 부피를 빼면 "대략" 필요한 증류수 부피가 나옴
    water_volume_ml = volume_ml - solute_volume_ml
    water_mass_g = water_volume_ml * WATER_DENSITY  # 부피(mL) x 밀도(g/mL) = 질량(g)
    water_volume_l = water_volume_ml / 1000

    # 사용자가 화면에서 고른 출력 단위(L / mL / g)에 맞는 값을 골라서 담음
    water_display = {"L": water_volume_l, "mL": water_volume_ml, "g": water_mass_g}[water_unit]

    return {
        "salt_name": salt["name"],
        "molar_mass": salt["molar_mass"],
        "density": salt["density"],
        "molarity": molarity,
        "needed_mass": needed_mass,
        "water_display": water_display,
        "water_unit": water_unit,
        "volume_ml": volume_ml,
        "prewater_ml": volume_ml * 0.7,  # "제조 방법" 2번 안내용: 처음에 미리 부어둘 증류수 양(전체의 70%)
    }

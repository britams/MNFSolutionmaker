document.getElementById("calc-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
        salt: document.getElementById("salt").value,
        conc_unit: document.getElementById("conc_unit").value,
        conc_value: document.getElementById("conc_value").value,
        volume_unit: document.getElementById("volume_unit").value,
        volume_value: document.getElementById("volume_value").value,
        water_unit: document.getElementById("water_unit").value,
    };

    const resultBox = document.getElementById("result");

    // 서버에 보내기 전에, 농도/부피 값이 0보다 큰지 먼저 확인합니다.
    // (음수나 0을 입력하면 계산이 성립하지 않으므로, 서버까지 가지 않고 바로 막습니다.)
    const numberFields = [
        ["conc_value", "몰농도"],
        ["volume_value", "용액의 부피"],
    ];
    for (const [id, label] of numberFields) {
        const value = Number(payload[id]);
        if (Number.isNaN(value) || value <= 0) {
            resultBox.className = "result error";
            resultBox.textContent = `${label} 값은 0보다 큰 숫자여야 합니다. (음수 입력 불가)`;
            resultBox.classList.remove("hidden");
            return;
        }
    }

    try {
        const res = await fetch("/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (!res.ok) {
            resultBox.className = "result error";
            resultBox.textContent = data.error || "오류가 발생했습니다.";
            resultBox.classList.remove("hidden");
            return;
        }

        resultBox.className = "result";
        resultBox.textContent =
`[결과값]
용질: ${data.salt_name} (몰질량 ${data.molar_mass.toFixed(2)} g/mol, 밀도 ${data.density.toFixed(2)} g/mL)
목표 농도: ${data.molarity.toFixed(2)} M
1. 필요한 ${data.salt_name} 질량: ${data.needed_mass.toFixed(2)} g
2. 필요한 증류수(근사값): ${data.water_display.toFixed(2)} ${data.water_unit}
3. 최종 용액 부피: ${data.volume_ml.toFixed(2)} mL

[제조 방법]
1. 저울로 ${data.salt_name} ${data.needed_mass.toFixed(2)}g을 정확히 측정합니다.
2. 비커에 증류수를 약 ${data.prewater_ml.toFixed(2)}mL 정도 먼저 붓습니다.
3. ${data.salt_name}을(를) 넣고 완전히 녹을 때까지 저어줍니다.
4. ${data.volume_ml.toFixed(2)}mL 메스플라스크에 용액을 옮깁니다.
5. 증류수를 메스플라스크의 눈금(표선)까지 천천히 추가하여 최종 부피를 맞춥니다.
6. 뚜껑을 닫고 충분히 흔들어 섞어줍니다.

※ 증류수 근사값은 20°C, 1 atm 기준 참고값이며, 실제 부피는 5번 과정의 표선 맞추기로 최종 결정됩니다.`;
        resultBox.classList.remove("hidden");
    } catch (err) {
        resultBox.className = "result error";
        resultBox.textContent = "서버와 통신할 수 없습니다.";
        resultBox.classList.remove("hidden");
    }
});

// script.js
// ------------------------------------------------------------------
// "계산하기"를 누르면 입력값을 모아 서버(app.py)의 /api/calculate 로 보내고,
// 결과를 받아 화면에 표시합니다.
// ------------------------------------------------------------------

const form = document.getElementById("calc-form");
const resultBox = document.getElementById("result");
const syringeFields = document.getElementById("syringeFields");
const channelFields = document.getElementById("channelFields");

// 단면적 계산 방식(주사기 / 채널)에 따라 해당 입력 영역만 보여줍니다.
document.querySelectorAll('input[name="areaMode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        const mode = document.querySelector('input[name="areaMode"]:checked').value;
        syringeFields.classList.toggle("hidden", mode !== "syringe");
        channelFields.classList.toggle("hidden", mode !== "channel");
    });
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const areaMode = document.querySelector('input[name="areaMode"]:checked').value;

    const payload = {
        areaMode: areaMode,
        syringe: document.getElementById("syringe").value,
        channelWidth: document.getElementById("channelWidth").value,
        channelHeight: document.getElementById("channelHeight").value,
        channelUnit: document.getElementById("channelUnit").value,
        inputValue: document.getElementById("inputValue").value,
        inputUnit: document.getElementById("inputUnit").value,
        outputUnit: document.getElementById("outputUnit").value,
    };

    // 서버에 보내기 전에 숫자 값들이 0보다 큰지 먼저 확인합니다.
    const numberFields = [["inputValue", "입력값"]];
    if (areaMode === "channel") {
        numberFields.push(["channelWidth", "채널 width"], ["channelHeight", "채널 height"]);
    }
    for (const [id, label] of numberFields) {
        const value = Number(payload[id]);
        if (Number.isNaN(value) || value <= 0) {
            showResult(`${label} 값은 0보다 큰 숫자여야 합니다.`, "error");
            return;
        }
    }

    try {
        const response = await fetch("/api/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
            showResult(data.error || "알 수 없는 오류가 발생했습니다.", "error");
            return;
        }

        showResult(
            `단면적(A): ${data.areaMm2.toFixed(4)} mm²\n` +
            `결과: ${data.resultValue} ${data.resultUnit}`,
            "success"
        );

    } catch (err) {
        showResult("서버에 연결할 수 없습니다.", "error");
    }
});

function showResult(message, type) {
    resultBox.textContent = message;
    resultBox.className = "result " + type;
}

// script.js
// ------------------------------------------------------------------
// 이 파일은 화면(index.html)에서 "계산하기" 버튼을 눌렀을 때
// 실제로 어떤 일이 일어나는지를 담당하는 자바스크립트 코드입니다.
//
// 흐름 요약:
//   1) 사용자가 폼(form)에 값을 입력하고 "계산하기"를 누른다.
//   2) 이 코드가 입력값을 모아서 백엔드 서버(app.py)의 /api/calculate 로 보낸다.
//   3) 서버가 계산해서 돌려준 결과(JSON)를 받아 화면에 표시한다.
// ------------------------------------------------------------------

// index.html 안에 있는 <form id="calc-form"> 요소를 찾아옵니다.
const form = document.getElementById("calc-form");
// 결과를 보여줄 <div id="result"> 요소를 찾아옵니다.
const resultBox = document.getElementById("result");

// form이 "제출(submit)"될 때, 즉 버튼을 눌렀을 때 실행할 함수를 등록합니다.
form.addEventListener("submit", async (event) => {
    // 원래 form을 제출하면 페이지가 새로고침되는데,
    // 우리는 새로고침 없이 자바스크립트로만 처리할 것이므로 그 기본 동작을 막습니다.
    event.preventDefault();

    // 각 입력창/선택창에서 사용자가 넣은 값을 읽어옵니다.
    const payload = {
        salt: document.getElementById("salt").value,
        stockConc: document.getElementById("stockConc").value,
        stockConcUnit: document.getElementById("stockConcUnit").value,
        workingConc: document.getElementById("workingConc").value,
        workingConcUnit: document.getElementById("workingConcUnit").value,
        workingVolume: document.getElementById("workingVolume").value,
        workingVolumeUnit: document.getElementById("workingVolumeUnit").value,
        stockOutUnit: document.getElementById("stockOutUnit").value,
        waterOutUnit: document.getElementById("waterOutUnit").value,
    };

    // 서버에 보내기 전에, 숫자 입력값(농도/부피)이 0보다 큰지 먼저 확인합니다.
    // (음수나 0을 넣으면 애초에 계산이 성립하지 않으므로, 서버까지 안 가고 바로 막습니다.)
    const numberFields = [
        ["stockConc", "stock solution 농도"],
        ["workingConc", "working solution 농도"],
        ["workingVolume", "working solution 양"],
    ];
    for (const [id, label] of numberFields) {
        const value = Number(payload[id]);
        if (Number.isNaN(value) || value <= 0) {
            showResult(`${label} 값은 0보다 큰 숫자여야 합니다. (음수 입력 불가)`, "error");
            return;
        }
    }

    try {
        // fetch() 는 자바스크립트에서 서버에 요청을 보내는 기본 함수입니다.
        // 여기서는 POST 방식으로 /api/calculate 주소에 payload(입력값들)를 JSON으로 보냅니다.
        const response = await fetch("/api/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        // 서버가 돌려준 응답을 JSON(자바스크립트 객체)으로 변환합니다.
        const data = await response.json();

        if (!response.ok) {
            // 서버가 에러를 돌려준 경우 (예: 잘못된 입력값)
            showResult(data.error || "알 수 없는 오류가 발생했습니다.", "error");
            return;
        }

        // 정상적으로 계산이 끝난 경우, stock 양과 증류수 양을 둘 다 화면에 보여줍니다.
        showResult(
            `필요한 stock solution 양: ${data.stockDisplayValue} ${data.stockDisplayUnit}\n` +
            `필요한 증류수 양: ${data.waterDisplayValue} ${data.waterDisplayUnit}`,
            "success"
        );

    } catch (err) {
        // 서버 자체에 연결이 안 되는 등 네트워크 문제가 있을 때
        showResult("서버에 연결할 수 없습니다. run.bat 으로 서버를 먼저 실행했는지 확인해주세요.", "error");
    }
});

// 결과 영역에 메시지를 표시해주는 함수입니다.
// type 값에 따라 초록색(success) 또는 빨간색(error)으로 스타일이 바뀝니다. (style.css 참고)
function showResult(message, type) {
    resultBox.textContent = message;
    resultBox.className = "result " + type;
}

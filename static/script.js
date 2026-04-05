const width = 600;
const height = 400;
const svg = d3.select("#viz");

// ネットワーク構成 (入力4, 隠れ5, 出力3)
const layerSizes = [4, 5, 3];




// 1. 左エリア

// 品種の色の定義（共通で使用）
const speciesColors = {
    "setosa": "#4285f4",     // 青
    "versicolor": "#ea4335", // 赤
    "virginica": "#34a853"   // 緑
};

// Irisデータの取得と表示（起動時に一度だけ実行）
async function loadIrisData() {
    try {
        const res = await fetch('/iris-data');
        const data = await res.json();

        // 左エリアを取得してテーブルを作成
        const leftArea = d3.select("#left-area");
        leftArea.append("h2").style("margin-left" , "50px").text("Iris Dataset");

        const table = leftArea.append("table")
            .style("width", "60%")
            .style("margin-left" , "50px")
            .style("border-collapse", "collapse")
            .style("font-size", "0.8rem");


        // Irisテーブルのヘッダーの作成．特徴名をボタンに
        const header = table.append("thead").append("tr");
        ["Sepal L", "Sepal W", "Petal L", "Petal W", "Species"].forEach((text, i) => {
            const th = header.append("th")
                            .style("border-bottom", "1px solid #ccc")
                            .style("text-align", "left");

            // 最初の4つ（特徴量）だけをボタン化する
            if (i < 4) {
                th.append("span")
                    .text(text)
                    .attr("class", "header-button selected") // 初期状態は選択中(selected)
                    .on("click", function() {
                        // 現在のクラスを確認し、selected と unselected を切り替える
                        const btn = d3.select(this);
                        const isSelected = btn.classed("selected");
                        btn.classed("selected", !isSelected);
                        btn.classed("unselected", isSelected);
                    });
            } else {
                // 品種名（Species）はボタンにしない
                th.text(text).style("padding", "5px");
            }
        });

        // データの表示（150行分）
        const tbody = table.append("tbody");
        data.forEach(d => {
            const row = tbody.append("tr");
            row.append("td").text(d.sepal_length.toFixed(1));
            row.append("td").text(d.sepal_width.toFixed(1));
            row.append("td").text(d.petal_length.toFixed(1));
            row.append("td").text(d.petal_width.toFixed(1));

            // 品種名に色を付ける
            row.append("td")
                .text(d.species)
                .style("color", speciesColors[d.species]) // 定義した色を適用
                .style("font-weight", "bold");
            // row.append("td").text(d.species);
        });

    } catch (err) {
        console.error("Failed to load Iris data:", err);
    }
}

// 実行
loadIrisData();



// 2. 右上エリア

// 2次元プロットの初期化
const plotWidth = 600;
const plotHeight = 400;
const plotMargin = { top: 20, right: 20, bottom: 40, left: 40 };

const plotSvg = d3.select("#right-top-area")
    .append("svg")
    .attr("id", "plot-viz")
    .attr("width", plotWidth)
    .attr("height", plotHeight)
    .style("background", "white")
    .style("border", "1px solid #ccc")
    .style("margin", "0 20px 20px 20px"); // 上 0, 右 20, 下 20, 左 20

// 軸を描画するためのグループを作成
const g = plotSvg.append("g")
    .attr("transform", `translate(${plotMargin.left},${plotMargin.top})`);

// 初期状態の軸（0.0〜1.0 の仮の範囲）
const xScale = d3.scaleLinear().domain([0, 1]).range([0, plotWidth - plotMargin.left - plotMargin.right]);
const yScale = d3.scaleLinear().domain([0, 1]).range([plotHeight - plotMargin.top - plotMargin.bottom, 0]);

const xAxis = g.append("g")
    .attr("class", "x-axis")
    .attr("transform", `translate(0, ${plotHeight - plotMargin.top - plotMargin.bottom})`)
    .call(d3.axisBottom(xScale));

const yAxis = g.append("g")
    .attr("class", "y-axis")
    .call(d3.axisLeft(yScale));



// 3. 右下エリア
const nodes = [];
const links = [];

// ①ノードの座標計算
layerSizes.forEach((size, lIdx) => {
    const x = (width / (layerSizes.length + 1)) * (lIdx + 1);
    for (let i = 0; i < size; i++) {
        const y = (height / (size + 1)) * (i + 1);
        nodes.push({ id: `l${lIdx}n${i}`, x, y, layer: lIdx });
    }
});

// ②リンク（エッジ）の作成
for (let i = 0; i < nodes.length; i++) {
    for (let j = 0; j < nodes.length; j++) {
        if (nodes[j].layer === nodes[i].layer + 1) {
            links.push({ source: nodes[i], target: nodes[j], weight: 0 });
        }
    }
}

// ③初期描画
const linkElements = svg.selectAll(".link")
    .data(links)
    .enter().append("line")
    .attr("class", "link")
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y)
    .attr("stroke", "#999")
    .attr("stroke-width", 1);

svg.selectAll(".node")
    .data(nodes)
    .enter().append("circle")
    .attr("class", "node")
    .attr("cx", d => d.x)
    .attr("cy", d => d.y)
    .attr("r", 15);


// ④SSEによるデータ受信の設定
const eventSource = new EventSource('/stream');

// EventSource を使ってサーバーからのストリームを常時監視
// データが届くたびに onmessage が発火し、D3.js の transition を使って描画を更新
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // テキスト更新
    document.getElementById('epoch').innerText = data.epoch;
    document.getElementById('loss').innerText = data.loss.toFixed(4);

    // 重みに基づいてリンクをアニメーション更新
    linkElements
        .transition().duration(300)
        .attr("stroke-width", (d, i) => Math.abs(data.weights[i]) * 8 + 1)
        .attr("stroke", (d, i) => data.weights[i] > 0 ? "#4285f4" : "#ea4335");
};

eventSource.onerror = (err) => {
    console.error("SSE error:", err);
    eventSource.close();
};


// ⑤学習制御ボタンのトグル動作（表示の切り替えのみ）
d3.select("#train-btn").on("click", function() {
    const btn = d3.select(this);
    
    if (btn.text() === "学習開始") {
        // サーバーに開始を命令
        fetch('/start', { method: 'POST' });

        // 停止状態へ移行
        btn.text("学習停止")
           .classed("btn-start", false)
           .classed("btn-stop", true);
    } else {
        // サーバーに停止を命令
        fetch('/stop', { method: 'POST' });
        
        // 開始状態へ移行
        btn.text("学習開始")
           .classed("btn-start", true)
           .classed("btn-stop", false);
    }
});


/*
Fetchのデータ更新ループ
async function update() {
    try {
        const res = await fetch('/status');
        const data = await res.json();

        // テキスト更新
        document.getElementById('epoch').innerText = data.epoch;
        document.getElementById('loss').innerText = data.loss.toFixed(4);

        // 重みに基づいてリンクをアニメーション更新
        linkElements
            .transition().duration(300)
            .attr("stroke-width", (d, i) => Math.abs(data.weights[i]) * 8 + 1)
            .attr("stroke", (d, i) => data.weights[i] > 0 ? "#4285f4" : "#ea4335");

    } catch (err) {
        console.error("Fetch error:", err);
    }
}

// 0.5秒ごとにAPIを叩く
setInterval(update, 500);
*/
const width = 600;
const height = 400;
const svg = d3.select("#viz");

// ネットワーク構成 (入力3, 隠れ4, 出力2)
const layerSizes = [3, 4, 2];
const nodes = [];
const links = [];

// 1. ノードの座標計算
layerSizes.forEach((size, lIdx) => {
    const x = (width / (layerSizes.length + 1)) * (lIdx + 1);
    for (let i = 0; i < size; i++) {
        const y = (height / (size + 1)) * (i + 1);
        nodes.push({ id: `l${lIdx}n${i}`, x, y, layer: lIdx });
    }
});

// 2. リンク（エッジ）の作成
for (let i = 0; i < nodes.length; i++) {
    for (let j = 0; j < nodes.length; j++) {
        if (nodes[j].layer === nodes[i].layer + 1) {
            links.push({ source: nodes[i], target: nodes[j], weight: 0 });
        }
    }
}

// 3. 初期描画
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

// 4. データ更新ループ
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
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import threading
import time
import numpy as np

# for SSE
import json
import asyncio
from fastapi.responses import StreamingResponse

# Irisオープンデータの利用
from sklearn.datasets import load_iris

# Irisデータセットを読み込む
iris = load_iris()

# 特徴量（4つの数値）を変数 iris_data にセット
iris_data = iris.data

# ラベル（0, 1, 2 の数値）を変数 iris_target にセット
iris_target = iris.target



app = FastAPI()

# --- 学習シミュレーションの状態 ---
# 入力3 -> 隠れ4 -> 出力2 (計20本の重み)
state = {
    "epoch": 0,
    "loss": 1.0,
    "weights": np.random.uniform(-1, 1, 20).tolist()
}

def train_simulation():
    """バックグラウンドで重みを更新し続ける関数"""
    global state
    while True:
        state["epoch"] += 1
        # Lossが徐々に減るシミュレーション
        state["loss"] *= 0.99
        # 重みが少しずつ変化するシミュレーション
        new_weights = [w + np.random.normal(0, 0.05) for w in state["weights"]]
        state["weights"] = new_weights
        
        time.sleep(0.5) # 0.5秒ごとに更新

# サーバー起動時に学習スレッドを開始
@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=train_simulation, daemon=True)
    thread.start()


# streamという口を開け、0.5秒ごとに最新のstateをストリームとして流し続ける
@app.get("/stream")
async def message_stream():
    async def event_generator():
        while True:
            # 状態をJSON文字列に変換し、SSEの形式（data: <内容>\n\n）で送る
            json_data = json.dumps(state)
            yield f"data: {json_data}\n\n"
            # 0.5秒待機
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


""" fetchリクエストを待ち受け
# --- APIエンドポイント ---
@app.get("/status")
async def get_status():
    return state

# --- 静的ファイルの配信 ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")
"""
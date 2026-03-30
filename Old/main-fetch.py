from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import threading
import time
import numpy as np

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

# --- APIエンドポイント ---
@app.get("/status")
async def get_status():
    return state

# --- 静的ファイルの配信 ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")
    
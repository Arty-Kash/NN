from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import threading
import time
import numpy as np
import json
import asyncio
from sklearn.datasets import load_iris

app = FastAPI()

# --- 1. Irisデータの読み込みと5グループ分割 ---
iris = load_iris()
iris_data = iris.data
iris_target = iris.target

# データをシャッフルする（品種の偏りをなくすため）
indices = np.arange(len(iris_data))
np.random.seed(42) # 学習の再現性のために固定
np.random.shuffle(indices)

shuffled_x = iris_data[indices]
shuffled_y = iris_target[indices]

# 150サンプルを5つのグループ（各30サンプル）に分ける
groups_x = np.array_split(shuffled_x, 5)
groups_y = np.array_split(shuffled_y, 5)

# ステップ2以降で使用するための変数定義
# 第1〜4グループ（120件）を学習用、第5グループ（30件）をテスト用とする
train_x = np.concatenate(groups_x[0:4])
train_y = np.concatenate(groups_y[0:4])
test_x = groups_x[4]
test_y = groups_y[4]

# --- 2. ニューラルネットワーククラスの定義 ---
class NeuralNetwork:
    def __init__(self, input_size, hidden_size, output_size):
        # 重みの初期化（ガウス分布）
        # 入力層4 -> 隠れ層5 (4x5=20個)
        self.w1 = np.random.randn(input_size, hidden_size) * 0.1
        # 隠れ層5 -> 出力層3 (5x3=15個)
        self.w2 = np.random.randn(hidden_size, output_size) * 0.1
        
        # バイアス（今回はシンプルにするため0で初期化）
        self.b1 = np.zeros((1, hidden_size))
        self.b2 = np.zeros((1, output_size))

    def forward(self, x):
        """順伝播（現在は枠組みのみ）"""
        pass

    def backward(self, x, y, output, learning_rate):
        """逆伝播（ステップ2で実装）"""
        pass

# NNインスタンスの生成（入力4, 隠れ5, 出力3）
nn_model = NeuralNetwork(input_size=4, hidden_size=5, output_size=3)

# --- 3. 学習状態の管理 ---

# 重みの総数は 20 + 15 = 35本
initial_weights = np.concatenate([nn_model.w1.flatten(), nn_model.w2.flatten()]).tolist()

state = {
    "epoch": 0,
    "loss": 1.0,
    "weights": initial_weights
}

is_running = False

def train_simulation():
    """バックグラウンドで重みを更新し続ける関数（現在はまだシミュレーション）"""
    global state
    while True:
        if is_running:
            state["epoch"] += 1
            state["loss"] *= 0.99
            # 重みが少しずつ変化するシミュレーション
            new_weights = [w + np.random.normal(0, 0.01) for w in state["weights"]]
            state["weights"] = new_weights
        
        time.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=train_simulation, daemon=True)
    thread.start()

# --- APIエンドポイント ---

@app.get("/iris-data")
async def get_iris_data():
    combined_data = []
    for i in range(len(iris_data)):
        combined_data.append({
            "sepal_length": iris_data[i][0],
            "sepal_width": iris_data[i][1],
            "petal_length": iris_data[i][2],
            "petal_width": iris_data[i][3],
            "species": iris.target_names[iris_target[i]]
        })
    return combined_data

@app.post("/start")
async def start_train():
    global is_running
    is_running = True
    return {"status": "ok"}

@app.post("/stop")
async def stop_train():
    global is_running
    is_running = False
    return {"status": "ok"}

@app.get("/stream")
async def message_stream():
    async def event_generator():
        while True:
            json_data = json.dumps(state)
            yield f"data: {json_data}\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import threading
import time
import numpy as np
import json
import asyncio
from sklearn.datasets import load_iris
import umap

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
# 第1グループ（30件）をテスト用、第2〜5グループ（120件）を学習用とする
test_x  = groups_x[0]
test_y  = groups_y[0]
train_x = np.concatenate(groups_x[1:])
train_y = np.concatenate(groups_y[1:])

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

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def softmax(self, x):
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)

    def forward(self, x):
        # 1. 入力層から隠れ層へ
        self.z1 = np.dot(x, self.w1) + self.b1
        self.a1 = self.sigmoid(self.z1)
        # 2. 隠れ層から出力層へ
        self.z2 = np.dot(self.a1, self.w2) + self.b2
        self.a2 = self.softmax(self.z2)
        return self.a2

    def backward(self, x, y, output, learning_rate):
        # 誤差の計算 (Cross Entropyの微分)
        m = y.shape[0]
        dz2 = output - y # 出力層の誤差
        
        # 隠れ層2 -> 出力層3 の重み更新量
        dw2 = np.dot(self.a1.T, dz2) / m
        db2 = np.sum(dz2, axis=0, keepdims=True) / m
        
        # 隠れ層の誤差 (シグモイド関数の微分を含む)
        da1 = np.dot(dz2, self.w2.T)
        dz1 = da1 * (self.a1 * (1 - self.a1))
        
        # 入力層4 -> 隠れ層5 の重み更新量
        dw1 = np.dot(x.T, dz1) / m
        db1 = np.sum(dz1, axis=0, keepdims=True) / m
        
        # 重みの更新 (勾配降下法)
        self.w1 -= learning_rate * dw1
        self.w2 -= learning_rate * dw2
        self.b1 -= learning_rate * db1
        self.b2 -= learning_rate * db2

# NNインスタンスの生成（入力4, 隠れ5, 出力3）
nn_model = NeuralNetwork(input_size=4, hidden_size=5, output_size=3)

# --- 3. 学習状態の管理 ---

# 重みの総数は 20 + 15 = 35本
initial_weights = np.concatenate([nn_model.w1.flatten(), nn_model.w2.flatten()]).tolist()

state = {
    "epoch": 0,
    "loss": 1.0,
    "weights": initial_weights, 
    "umap_coords": [] # 150個の [x, y] リストが入る
}

is_running = False

def train_simulation():
    global state
    # ラベル（0, 1, 2）をOne-Hot形式に変換（例: 0 -> [1, 0, 0]）
    train_y_onehot = np.eye(3)[train_y]
    
    learning_rate = 0.1 # 学習率

    # UMAPの計算器（2次元に圧縮）
    reducer = umap.UMAP(n_components=2, random_state=42)

    while True:
        if is_running:
            # 1. 順伝播（予測）
            output = nn_model.forward(train_x)
            
            # 2. 誤差（Loss）の計算：交差エントロピー誤差
            m = train_y.shape[0]
            loss = -np.sum(train_y_onehot * np.log(output + 1e-8)) / m
            
            # 3. 逆伝播（学習）
            nn_model.backward(train_x, train_y_onehot, output, learning_rate)
            
            # stateの更新（フロントエンド配信用）
            state["epoch"] += 1
            state["loss"] = float(loss)
            # 現在の重みをリスト化して反映
            state["weights"] = np.concatenate([nn_model.w1.flatten(), nn_model.w2.flatten()]).tolist()
        
            # --- UMAP計算ロジック（50エポックごと） ---
            if state["epoch"] % 50 == 0:
                # 全150サンプルの隠れ層（a1）の出力を取得
                # ※forwardを呼ぶとインスタンスの self.a1 が更新される
                nn_model.forward(shuffled_x)
                hidden_outputs = nn_model.a1 # (150, 5) の行列
                
                # UMAPで (150, 5) -> (150, 2) に圧縮
                embedding = reducer.fit_transform(hidden_outputs)
                
                # 0〜1の範囲に正規化（描画しやすくするため）
                min_val = embedding.min(axis=0)
                max_val = embedding.max(axis=0)
                normalized = (embedding - min_val) / (max_val - min_val + 1e-8)
                
                state["umap_coords"] = normalized.tolist()

        time.sleep(0.1) # 学習スピードを少し上げるために待機時間を短縮

        

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=train_simulation, daemon=True)
    thread.start()

# --- APIエンドポイント ---
@app.get("/iris-data")
async def get_iris_data():
    # 150行分のデータを整形してリスト形式で返す
    combined_data = []
    for i in range(len(shuffled_x)):
        # 150件のうち、30番目まで（第１グループ）をテスト用(is_test=True)とする
        is_test = i < 30
        
        combined_data.append({
            "sepal_length": shuffled_x[i][0],
            "sepal_width": shuffled_x[i][1],
            "petal_length": shuffled_x[i][2],
            "petal_width": shuffled_x[i][3],
            "species": iris.target_names[shuffled_y[i]],
            "is_test": is_test  # 【追加】テスト用かどうかのフラグ
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

@app.get("/predict")
async def get_predict():
    # テストデータ30件に対して現在の重みで順伝播（予測）を行う
    output = nn_model.forward(test_x)
    # 最も確率が高い品種のインデックスを取得
    predictions = np.argmax(output, axis=1)
    # インデックス(0,1,2)を品種名("setosa"等)に変換してリストで返す
    pred_names = [iris.target_names[p] for p in predictions]
    return pred_names
    
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")
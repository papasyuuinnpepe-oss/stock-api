import time
import yfinance as yf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FILE = "codes.json"

# 🔥 初期ロード
if os.path.exists(FILE):
    with open(FILE, "r") as f:
        codes = json.load(f)
else:
    codes = ["6098.T", "7203.T"]

# 🔥 保存
def save_codes():
    with open(FILE, "w") as f:
        json.dump(codes, f)

class CodeRequest(BaseModel):
    code: str

# 🔥 追加
@app.post("/add")
def add_code(req: CodeRequest):
    code = req.code.strip().upper()

    if code not in codes:
        codes.append(code)
        save_codes()

    return {"codes": codes}

# 🔥 削除
@app.post("/delete")
def delete_code(req: CodeRequest):
    code = req.code.strip().upper()

    if code in codes:
        codes.remove(code)
        save_codes()

    return {"codes": codes}

# 🔥 キャッシュ
cache = None
last_update = 0

# 🔥 スキャン（高速版）
@app.get("/scan")
def scan():
    global cache, last_update

    if time.time() - last_update < 30 and cache is not None:
        return cache

    result = []

    print("START DOWNLOAD")

    data = yf.download(
        tickers=" ".join(codes),
        period="2d",
        group_by="ticker",
        threads=True
    )

    print("DOWNLOAD DONE")

    for code in codes:
        try:
            if code not in data:
                continue

            info = data[code]

            if len(info) < 2:
                continue

            today = info.iloc[-1]
            yesterday = info.iloc[-2]

            price = float(today["Close"])
            open_price = float(today["Open"])
            volume = int(today["Volume"])
            prev_volume = int(yesterday["Volume"])

            change = (price - open_price) / open_price * 100
            volume_ratio = volume / prev_volume if prev_volume > 0 else 1

            hit = change > 2 and volume_ratio > 1.5
            score = round(change * 10 + volume_ratio * 5, 1)

            result.append({
                "code": code,
                "price": round(price, 1),
                "change": round(change, 2),
                "volume": volume,
                "volume_ratio": round(volume_ratio, 2),
                "score": score,
                "hit": hit
            })

        except Exception as e:
            print("ERROR:", code, e)

    ranked = sorted(result, key=lambda x: x["score"], reverse=True)

    cache = ranked
    last_update = time.time()

    print("END")

    return ranked
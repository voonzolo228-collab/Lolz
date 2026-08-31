from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import os
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "users.json"

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

CASES = [
    {"id": 1, "name": "Стандартний", "price": 50, "items": [
        {"name": "🎁 Звичайний", "rarity": "common", "emoji": "🎁"},
        {"name": "🎀 Рідкісний", "rarity": "rare", "emoji": "🎀"},
        {"name": "💎 Епічний", "rarity": "epic", "emoji": "💎"},
        {"name": "👑 Легендарний", "rarity": "legendary", "emoji": "👑"}
    ]},
    {"id": 2, "name": "Преміум", "price": 150, "items": [
        {"name": "🏆 Золотий", "rarity": "epic", "emoji": "🏆"},
        {"name": "⭐ Платиновий", "rarity": "legendary", "emoji": "⭐"},
        {"name": "🔥 Міфічний", "rarity": "legendary", "emoji": "🔥"},
        {"name": "🌌 Космічний", "rarity": "legendary", "emoji": "🌌"}
    ]},
    {"id": 3, "name": "Безкоштовний", "price": 0, "items": [
        {"name": "🪙 Монетка", "rarity": "common", "emoji": "🪙"},
        {"name": "🔮 Наклейка", "rarity": "common", "emoji": "🔮"},
        {"name": "😎 Смайлик", "rarity": "rare", "emoji": "😎"}
    ]}
]

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/api/user/{telegram_id}")
def get_user(telegram_id: int):
    users = load_users()
    user_id = str(telegram_id)
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
        save_users(users)
    return {"stars": users[user_id]["stars"], "inventory": users[user_id]["inventory"]}

@app.post("/api/open_case")
def open_case(data: dict):
    telegram_id = str(data.get("telegram_id"))
    case_id = data.get("case_id")
    
    users = load_users()
    if telegram_id not in users:
        users[telegram_id] = {"stars": 300, "inventory": [], "promos_used": []}
    
    case = next((c for c in CASES if c["id"] == case_id), None)
    if not case:
        raise HTTPException(400, "Кейс не знайдено")
    
    if case["price"] > 0 and users[telegram_id]["stars"] < case["price"]:
        raise HTTPException(400, "Недостатньо зірок")
    
    users[telegram_id]["stars"] -= case["price"]
    item = random.choice(case["items"])
    users[telegram_id]["inventory"].append(item)
    save_users(users)
    
    return {"item": item, "balance": users[telegram_id]["stars"], "inventory": users[telegram_id]["inventory"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

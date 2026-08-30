from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import random
from database import SessionLocal, User, GiftCase, PromoCode

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/api/user/{telegram_id}")
def get_user(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, stars_balance=300)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"id": user.id, "telegram_id": user.telegram_id, "stars_balance": user.stars_balance, "inventory": user.inventory or []}

@app.post("/api/user/{telegram_id}/give_stars")
def give_stars(telegram_id: int, amount: int = 300, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    user.stars_balance += amount
    db.commit()
    return {"balance": user.stars_balance}

@app.post("/api/cases/open/{case_id}")
def open_case(case_id: int, telegram_id: int, promo_code: str = None, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        raise HTTPException(404, "Користувача не знайдено")
    
    gift_case = db.query(GiftCase).filter_by(id=case_id, is_active=True).first()
    if not gift_case:
        raise HTTPException(404, "Кейс не знайдено")
    
    if promo_code:
        promo = db.query(PromoCode).filter_by(code=promo_code, is_active=True).first()
        if not promo or promo.uses_left <= 0:
            raise HTTPException(400, "Невірний промокод")
        
        if promo.case_id and promo.case_id != case_id:
            raise HTTPException(400, "Промокод не для цього кейсу")
        
        promo.uses_left -= 1
        if promo.uses_left <= 0:
            promo.is_active = False
        
        if promo.stars_amount > 0:
            user.stars_balance += promo.stars_amount
            db.commit()
            return {"item": random.choice(gift_case.items), "balance": user.stars_balance, "promo_used": True}
    else:
        if gift_case.price_stars > 0 and user.stars_balance < gift_case.price_stars:
            raise HTTPException(400, "Недостатньо зірок")
        user.stars_balance -= gift_case.price_stars
    
    win_item = random.choice(gift_case.items)
    if not user.inventory:
        user.inventory = []
    user.inventory.append(win_item)
    db.commit()
    
    return {"item": win_item, "balance": user.stars_balance, "promo_used": False}

@app.get("/api/cases")
def get_cases(db: Session = Depends(get_db)):
    return db.query(GiftCase).filter_by(is_active=True).all()

@app.get("/api/promo/check/{code}")
def check_promo(code: str, db: Session = Depends(get_db)):
    promo = db.query(PromoCode).filter_by(code=code, is_active=True).first()
    if promo and promo.uses_left > 0:
        return {"valid": True, "case_id": promo.case_id, "stars": promo.stars_amount}
    return {"valid": False}

@app.get("/api/inventory/{telegram_id}")
def get_inventory(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        return {"inventory": []}
    return {"inventory": user.inventory or []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

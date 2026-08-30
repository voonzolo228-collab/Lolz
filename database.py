from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    stars_balance = Column(Integer, default=300)
    inventory = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class GiftCase(Base):
    __tablename__ = 'gift_cases'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price_stars = Column(Integer, nullable=False)
    items = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    case_id = Column(Integer, nullable=True)
    stars_amount = Column(Integer, default=0)
    uses_left = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

engine = create_engine('sqlite:///gift_battle.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    db = SessionLocal()
    if db.query(GiftCase).count() == 0:
        cases = [
            GiftCase(name="Стандартний кейс", price_stars=50, items=[
                {"name": "Звичайний подарунок", "rarity": "common", "emoji": "🎁"},
                {"name": "Рідкісний подарунок", "rarity": "rare", "emoji": "🎀"},
                {"name": "Епічний подарунок", "rarity": "epic", "emoji": "💎"},
                {"name": "Легендарний подарунок", "rarity": "legendary", "emoji": "👑"}
            ]),
            GiftCase(name="Преміум кейс", price_stars=150, items=[
                {"name": "Золотий подарунок", "rarity": "epic", "emoji": "🏆"},
                {"name": "Платиновий подарунок", "rarity": "legendary", "emoji": "⭐"},
                {"name": "Міфічний подарунок", "rarity": "legendary", "emoji": "🔥"},
                {"name": "Космічний подарунок", "rarity": "legendary", "emoji": "🌌"}
            ]),
            GiftCase(name="Безкоштовний кейс", price_stars=0, items=[
                {"name": "Монетка", "rarity": "common", "emoji": "🪙"},
                {"name": "Наклейка", "rarity": "common", "emoji": "🔮"},
                {"name": "Смайлик", "rarity": "rare", "emoji": "😎"}
            ])
        ]
        db.add_all(cases)
    
    if db.query(PromoCode).count() == 0:
        promos = [
            PromoCode(code="GIFT2024", stars_amount=100, uses_left=10),
            PromoCode(code="FREEBOX", case_id=3, uses_left=5),
            PromoCode(code="STAR500", stars_amount=500, uses_left=3)
        ]
        db.add_all(promos)
    
    db.commit()
    db.close()

init_db()

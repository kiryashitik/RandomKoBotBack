import os
import random
import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, 
    WebAppInfo, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from fastapi import FastAPI, Request
import uvicorn
from database import User, Contest, get_db

# Инициализация FastAPI для обработки запросов от Mini App
app = FastAPI()

# Настройка CORS для FastAPI
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Конфигурация
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8252785543:AAFjc_rvmMhZqsqllX3uhP0XDHmwOTuqURA")
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "mane_karl")
    WEBAPP_URL = os.getenv("WEBAPP_URL", "https://admirable-pixie-edae72.netlify.app/")
    ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[527228466]"))
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

# Инициализация бота
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Обработчик стартовой команды
@router.message(Command("start"))
async def start(message: Message):
    web_app = WebAppInfo(url=Config.WEBAPP_URL)
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть Mini App", web_app=web_app)]],
        resize_keyboard=True
    )
    
    if message.from_user.id in Config.ADMIN_IDS:
        builder = ReplyKeyboardBuilder()
        builder.button(text="Админ-панель")
        markup = builder.as_markup(resize_keyboard=True)
    
    await message.answer(
        "Добро пожаловать в бота для конкурсов! 🎉",
        reply_markup=markup
    )

# Админ-панель
@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.answer("❌ Доступ запрещён")
    
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Старт конкурса")
    builder.button(text="⏹ Стоп конкурса")
    builder.button(text="📊 Статистика")
    builder.button(text="🔙 Назад")
    builder.adjust(2)
    
    await message.answer(
        "👨‍💻 Панель администратора:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Обработчики админ-команд
@router.message(F.text == "🔄 Старт конкурса")
async def start_contest(message: Message):
    db = next(get_db())
    active_contest = db.query(Contest).filter_by(is_active=True).first()
    
    if active_contest:
        return await message.answer("⚠️ Конкурс уже активен")
    
    new_contest = Contest(is_active=True)
    db.add(new_contest)
    db.commit()
    await message.answer("✅ Конкурс запущен!")

@router.message(F.text == "⏹ Стоп конкурса")
async def stop_contest(message: Message):
    db = next(get_db())
    contest = db.query(Contest).filter_by(is_active=True).first()
    
    if not contest:
        return await message.answer("⚠️ Нет активных конкурсов")
    
    participants = db.query(User).filter_by(is_participated=True).all()
    if participants:
        winner = random.choice(participants)
        contest.winner_id = winner.user_id
        await message.answer(
            f"🏆 Победитель: @{winner.username}\n"
            f"ID: {winner.user_id}"
        )
    
    contest.is_active = False
    db.commit()
    await message.answer("✅ Конкурс завершён")

@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    db = next(get_db())
    active = db.query(Contest).filter_by(is_active=True).first()
    participants = db.query(User).filter_by(is_participated=True).count()
    
    await message.answer(
        f"📊 Статистика:\n\n"
        f"• Активный конкурс: {'✅ Да' if active else '❌ Нет'}\n"
        f"• Участников: {participants}"
    )

@router.message(F.text == "🔙 Назад")
async def back_to_main(message: Message):
    await start(message)

# Обработчик данных из Mini App
@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        if data.get('action') == 'participate':
            db = next(get_db())
            user = db.query(User).filter_by(user_id=user_id).first()
            
            if not user:
                user = User(
                    user_id=user_id,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name,
                    is_participated=True
                )
                db.add(user)
            else:
                user.is_participated = True
            
            db.commit()
            await message.answer(
                "🎉 Вы участвуете в конкурсе!",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

# FastAPI endpoint для проверки подписки
@app.post("/check_subscription")
async def check_subscription(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    channel = data.get('channel')
    
    try:
        member = await Config.bot.get_chat_member(
            chat_id=f"@{channel}",
            user_id=user_id
        )
        return {
            "is_subscribed": member.status in [
                "member", "administrator", "creator"
            ]
        }
    except Exception as e:
        return {"error": str(e)}

# Запуск приложения
async def run_bot():
    await dp.start_polling(Config.bot)

if __name__ == "__main__":
    import asyncio
 
    # Запуск бота
    asyncio.run(run_bot())
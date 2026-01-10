import os
import subprocess
import logging
import mss
import signal
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# -------------------------------------------------------
# Налаштування
# -------------------------------------------------------
BOT_TOKEN = "token" 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ALLOWED_CHATS = {id}

def _chat_allowed(update: Update) -> bool:
    if not ALLOWED_CHATS:
        return True
    return update.effective_chat.id in ALLOWED_CHATS

# -------------------------------------------------------
# Клавіатура
# -------------------------------------------------------

def get_main_keyboard():
    # Змінено назву кнопки для зрозумілості
    keyboard = [
        [KeyboardButton("📸 Screenshot"), KeyboardButton("🔒 Lock PC")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# -------------------------------------------------------
# Допоміжні функції
# -------------------------------------------------------

def lock_windows_pc():
    """Виконує команду блокування робочої станції"""
    try:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return True
    except Exception as e:
        logging.error(f"Помилка блокування: {e}")
        return False

# -------------------------------------------------------
# Обробники команд
# -------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return

    await update.message.reply_text(
        "👋 Бот готовий до роботи!\n\n"
        "/run <команда> – термінал\n"
        "/shot – скріншот\n"
        "/lock – заблокувати Windows",
        reply_markup=get_main_keyboard(),
    )

async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /lock"""
    if not _chat_allowed(update):
        return
    
    if lock_windows_pc():
        await update.message.reply_text("🔒 Комп'ютер заблоковано.")
    else:
        await update.message.reply_text("⚠️ Не вдалося виконати команду блокування.")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _chat_allowed(update): return
    
    user_input = update.message.text.strip()
    if not user_input.startswith("/run "):
        await update.message.reply_text("❌ Формат: `/run <команда>`")
        return

    command = user_input[5:].strip()
    try:
        # Для MarkdownV2 важливо екранувати спецсимволи, але для простоти виводу
        # ми використаємо простий блок коду
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = (result.stdout + result.stderr).strip() or "(немає виводу)"
        await update.message.reply_text(f"📝 **Результат:**\n```\n{output[:3500]}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {e}")

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _chat_allowed(update): return
    try:
        screenshot_path = "screenshot.png"
        with mss.mss() as sct:
            sct.shot(output=screenshot_path)
        
        with open(screenshot_path, "rb") as f:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f, caption="Ваш скріншот 📸")
        os.remove(screenshot_path) # Видаляємо файл після відправки
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка скріншоту: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _chat_allowed(update): return
    text = update.message.text
    
    if text == "📸 Screenshot":
        await screenshot_handler(update, context)
    elif text == "🔒 Lock PC":
        if lock_windows_pc():
            await update.message.reply_text("🔒 Комп'ютер заблоковано.")
        else:
            await update.message.reply_text("⚠️ Помилка виконання.")
    else:
        await update.message.reply_text("❓ Оберіть дію на клавіатурі.")

# -------------------------------------------------------
# Основна функція
# -------------------------------------------------------

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lock", lock_command))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("shot", screenshot_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    logging.info("🚀 Бот запущений...")
    application.run_polling()

if __name__ == "__main__":
    main()


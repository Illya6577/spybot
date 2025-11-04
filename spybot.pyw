import os
import subprocess
import logging
import mss
import signal
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# -------------------------------------------------------
# Налаштування
# -------------------------------------------------------
BOT_TOKEN = "token"  # Замініть на ваш реальний токен

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Білий список користувачів (chat_id)
ALLOWED_CHATS = {id}  # Ваш chat_id тут

def _chat_allowed(update: Update) -> bool:
    """Перевіряє, чи надходять повідомлення від дозволених користувачів."""
    if not ALLOWED_CHATS:
        return True
    return update.effective_chat.id in ALLOWED_CHATS

# Глобальна змінна для доступу до application
app_instance = None

def signal_handler(signum, frame):
    """Обробник сигналів для коректного завершення"""
    logging.info("🛑 Отримано сигнал завершення. Зупиняю бота...")
    if app_instance:
        app_instance.stop()
    exit(0)

# -------------------------------------------------------
# Клавіатура з кнопками
# -------------------------------------------------------

def get_main_keyboard():
    """Створює клавіатуру з двома кнопками"""
    keyboard = [
        [KeyboardButton("📸 Screenshot"), KeyboardButton("⏹️ Stop")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# -------------------------------------------------------
# Обробники команд
# -------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return

    await update.message.reply_text(
        "👋 Привіт! Оберіть дію з клавіатури нижче або використайте команди:\n"
        "/run <команда> – виконати команду в терміналі\n"
        "/shot – зробити скріншот\n"
        "/stop – зупинити бота",
        reply_markup=get_main_keyboard(),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return
    await update.message.reply_text(
        "📋 Доступні команди:\n"
        "/run <команда> – виконати команду в терміналі\n"
        "/shot – зробити скріншот\n"
        "/stop – зупинити бота\n\n"
        "Або використайте кнопки внизу 👇",
        reply_markup=get_main_keyboard(),
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stop"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return
    
    await update.message.reply_text("🛑 Зупиняю бота...")
    global app_instance
    if app_instance:
        app_instance.stop()

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Виконує команду, передану після /run"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return

    user_input = update.message.text.strip()
    
    if not user_input.startswith("/run "):
        await update.message.reply_text(
            "❌ Неправильний формат. Використовуйте: `/run <команда>`"
        )
        return

    command = user_input[5:].strip()
    if not command:
        await update.message.reply_text("❌ Будь ласка, вкажіть команду після `/run`.")
        return

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        err = result.stderr.strip()

        if err:
            output = f"[stderr]\n{err}\n[stdout]\n{output}"

        if not output:
            output = "(команда завершилась без виводу)"

        await update.message.reply_text(
            f"**Вивід команди:**\n```\n{output}\n```",
            parse_mode="MarkdownV2",
        )

    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ Команда зайняла занадто багато часу.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при виконанні: `{e}`")

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробка скріншота"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return

    try:
        screenshot_path = "/tmp/telegram_screenshot.png"
        
        # Використовуємо mss для створення скріншоту
        with mss.mss() as sct:
            sct.shot(output=screenshot_path)
        
        with open(screenshot_path, "rb") as f:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=f,
                caption="Ваш скріншот 📸",
            )
    except Exception as e:
        await update.message.reply_text(
            f"Не вдалося зробити скріншот: `{e}`"
        )

async def shot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /shot"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return
    await screenshot_handler(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник натискання кнопок"""
    if not _chat_allowed(update):
        await update.message.reply_text("❌ Доступ заборонено.")
        return

    text = update.message.text
    
    if text == "📸 Screenshot":
        await screenshot_handler(update, context)
    elif text == "⏹️ Stop":
        await update.message.reply_text("🛑 Зупиняю бота...")
        global app_instance
        if app_instance:
            app_instance.stop()
    else:
        await update.message.reply_text(
            "❓ Не зрозуміла команда. Використайте кнопки або команди.",
            reply_markup=get_main_keyboard(),
        )

# -------------------------------------------------------
# Основна функція
# -------------------------------------------------------

def main() -> None:
    """Запуск бота"""
    global app_instance
    
    try:
        logging.info("🤖 Починаю ініціалізацію бота...")
        application = Application.builder().token(BOT_TOKEN).build()
        app_instance = application  # Зберігаємо посилання для зупинки
        
        # Обробники команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("run", run_command))
        application.add_handler(CommandHandler("shot", shot_command))
        application.add_handler(CommandHandler("stop", stop_command))

        # Обробник натискання кнопок
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

        # Реєструємо обробники сигналів
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logging.info("🚀 Запуск polling...")
        application.run_polling()
    except Exception as e:
        logging.error(f"❌ Помилка запуску бота: {e}")
        print(f"❌ Помилка запуску бота: {e}")

if __name__ == "__main__":
    main()
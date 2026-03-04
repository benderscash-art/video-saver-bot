import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp

# Токен берём из переменной окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Video Saver 24/7*\n\n"
        "📥 YouTube, TikTok, Instagram\n"
        "🎵 Конвертация в MP3\n"
        "⚡ Быстро и бесплатно\n\n"
        "🚀 *Отправь ссылку на видео!*"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Это не ссылка. Отправь URL.")
        return
    
    msg = await update.message.reply_text("⏳ *Обрабатываю...*")
    
    try:
        ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True, 'no_warnings': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Video')
            duration = info.get('duration', 0)
            
            # Ограничение 20 мин для бесплатного тарифа
            if duration > 1200:
                await msg.edit_text("⚠️ Бесплатно до 20 мин.\n💎 Premium для длинных видео!")
                return
            
            formats = info.get('formats', [])
            keyboard = []
            
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    height = f.get('height', 0)
                    filesize = f.get('filesize', 0)
                    size_mb = round(filesize / 1024 / 1024, 1) if filesize else '?'
                    
                    if height in [1080, 720, 480, 360]:
                        keyboard.append([
                            InlineKeyboardButton(f"🎬 {height}p • {size_mb} MB", 
                                               callback_data=f"video_{height}_{url}")
                        ])
            
            keyboard.append([InlineKeyboardButton("🎵 MP3 Аудио", callback_data=f"audio_0_{url}")])
            
            await msg.edit_text(
                f"📥 *{title}*\n\n⏱ {duration//60}:{duration%60:02d}\n\n*Выбери качество:*",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    action, quality = parts[0], parts[1]
    url = '_'.join(parts[2:])
    
    await query.message.reply_text("⏳ *Скачиваю...*")
    
    try:
        ydl_opts = {'outtmpl': 'download.%(ext)s', 'quiet': True, 'no_warnings': True}
        
        if action == "video":
            ydl_opts['format'] = f"best[height={quality}][ext=mp4]/best[height<={quality}]"
        elif action == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            
            if action == "audio":
                filepath = filepath.rsplit('.', 1)[0] + '.mp3'
            
            title = info.get('title', 'Video')
            
            if action == "video":
                await query.message.reply_video(
                    video=open(filepath, 'rb'),
                    caption=f"✅ *{title}*\n\n🎬 {quality}p"
                )
            else:
                await query.message.reply_audio(
                    audio=open(filepath, 'rb'),
                    caption=f"✅ *{title}*\n\n🎵 MP3"
                )
            
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        await query.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()


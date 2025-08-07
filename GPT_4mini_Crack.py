import json
import os
import asyncio
import sqlite3
import httpx
import logging
import nest_asyncio
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp
import re
from datetime import datetime

# تهيئة التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تطبيق nest_asyncio
nest_asyncio.apply()

# إعدادات API
TELEGRAM_TOKEN = '7577600321:AAHtmaeQmGca3nhxD--_tYxYlUdNyxElz18'
API_KEY = 'AIzaSyCZVuenJfMv6I7uOdSm7zRRfmk2ety-GF0'
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}'
previous_message_id = None

# حالة الذكاء الاصطناعي
ai_available = True

# تهيئة تطبيق Flask
app = Flask(__name__)

# إعداد قاعدة البيانات
BASE_DIR = Path(__file__).parent
DB_NAME = BASE_DIR / 'bot_data.db'

def initialize_database():
    """تهيئة قاعدة البيانات وإنشاء الجداول إذا لزم الأمر"""
    try:
        # إنشاء مجلد التحميلات إذا لم يكن موجودًا
        os.makedirs(BASE_DIR / 'downloads', exist_ok=True)
        
        # إنشاء ملف قاعدة البيانات إذا لم يكن موجودًا
        if not DB_NAME.exists():
            DB_NAME.touch(mode=0o666, exist_ok=True)
        
        # الاتصال بقاعدة البيانات وإنشاء الجداول
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    timestamp TEXT
                )
            ''')
            
            # جدول المستخدمين النشطين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_users (
                    id INTEGER PRIMARY KEY
                )
            ''')
            
            conn.commit()
            logger.info("تم تهيئة قاعدة البيانات بنجاح")
            
    except Exception as e:
        logger.error(f"فشل في تهيئة قاعدة البيانات: {e}")
        raise

initialize_database()

# مسارات Flask
@app.route('/previous_users', methods=['GET'])
def previous_users():
    """عرض المستخدمين السابقين"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users 
                WHERE id NOT IN (SELECT DISTINCT id FROM active_users)
            ''')
            previous_users_list = cursor.fetchall()
        return render_template('previous_users.html', previous_users=previous_users_list)
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين السابقين: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/active_users', methods=['GET'])
def active_users():
    """عرض المستخدمين النشطين"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users 
                WHERE id IN (SELECT DISTINCT id FROM active_users)
            ''')
            active_users_list = cursor.fetchall()
        return render_template('active_users.html', active_users=active_users_list)
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين النشطين: {e}")
        return jsonify({"error": str(e)}), 500

# وظائف المساعدة
def clean_filename(filename: str) -> str:
    """تنظيف اسم الملف من الأحرف غير المسموح بها"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename[:255]

async def shorten_url(long_url: str) -> str:
    """تقصير الروابط باستخدام TinyURL"""
    url = f"https://tinyurl.com/api-create.php?url={long_url}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"خطأ في تقصير الرابط: {e}")
            raise

# معالجات Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /start"""
    welcome_message = (
        "✨ مرحبًا بك في بوتنا الذكي! ✨\n\n"
        "يمكنك استخدام الأوامر التالية:\n"
        "• /help - عرض قائمة المساعدة\n"
        "• أرسل رابطًا لتقصيره أو لتنزيل الفيديو"
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message
        )
        
        # تسجيل المستخدم في قاعدة البيانات
        user = update.effective_user
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (id, username, timestamp)
                VALUES (?, ?, ?)
            ''', (user.id, user.username or "مجهول", datetime.now().isoformat()))
            cursor.execute('INSERT OR IGNORE INTO active_users (id) VALUES (?)', (user.id,))
            conn.commit()
            
        logger.info(f"مستخدم جديد: {user.username} (ID: {user.id})")
        
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر /help"""
    help_text = (
        "🛠️ قائمة المساعدة:\n\n"
        "• تقصير الروابط: أرسل أي رابط وسأقوم بتقصيره\n"
        "• تنزيل الفيديو: أرسل رابط فيديو من YouTube/TikTok/Instagram\n"
        "• الدردشة: يمكنك التحدث معي مباشرة!\n\n"
        "لتجربة الميزات، أرسل لي رابطًا أو رسالة عادية."
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text
        )
    except Exception as e:
        logger.error(f"خطأ في معالجة أمر /help: {e}")

async def ask_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """عرض خيارات للمستخدم للرابط المرسل"""
    try:
        keyboard = [
            [
                InlineKeyboardButton("📎 تقصير الرابط", callback_data=f"shorten_{url}"),
                InlineKeyboardButton("🎬 تنزيل الفيديو", callback_data=f"download_{url}"),
            ]
        ]
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="ما الذي تريد أن تفعله بهذا الرابط؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطأ في عرض خيارات الرابط: {e}")

async def handle_video_download(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تنزيل الفيديو من الرابط"""
    try:
        # إعداد خيارات yt-dlp
        ydl_opts = {
            'format': 'best',
            'outtmpl': str(BASE_DIR / 'downloads' / '%(title)s.%(ext)s'),
            'quiet': True,
        }
        
        # إرسال رسالة الانتظار
        wait_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ جاري معالجة طلبك، يرجى الانتظار..."
        )
        
        # تنزيل الفيديو
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            clean_path = BASE_DIR / 'downloads' / clean_filename(os.path.basename(video_path))
            
            # تجنب تكرار الأسماء
            if clean_path.exists():
                base, ext = os.path.splitext(clean_path)
                counter = 1
                while clean_path.exists():
                    clean_path = Path(f"{base}_{counter}{ext}")
                    counter += 1
            
            os.rename(video_path, clean_path)
            
            # إرسال الفيديو
            with open(clean_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption="✅ تم تنزيل الفيديو بنجاح"
                )
            
            # حذف رسالة الانتظار
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=wait_msg.message_id
            )
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"خطأ في تنزيل الفيديو: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ تعذر تنزيل الفيديو، يرجى التأكد من صحة الرابط"
        )
    except Exception as e:
        logger.error(f"خطأ غير متوقع في تنزيل الفيديو: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ حدث خطأ غير متوقع، يرجى المحاولة لاحقًا"
        )
    finally:
        # تنظيف الملف المؤقت إذا وجد
        if 'clean_path' in locals() and clean_path.exists():
            try:
                os.remove(clean_path)
            except:
                pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الصور المرسلة"""
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📸 لمعالجة الصور، يرجى استخدام بوت معالجة الصور:\n@AIEditImagebot"
        )
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {e}")

async def respond_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرد على الرسائل النصية"""
    global ai_available
    
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    
    # معالجة الأوامر الخاصة
    if text.startswith('/'):
        return
    
    # معالجة الروابط
    if text.startswith(('http://', 'https://')):
        try:
            await ask_for_action(update, context, text)
            return
        except Exception as e:
            logger.error(f"خطأ في معالجة الرابط: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ حدث خطأ في معالجة الرابط"
            )
            return
    
    # معالجة الرسائل النصية بالذكاء الاصطناعي
    if not ai_available:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ عذرًا، خدمة الذكاء الاصطناعي غير متاحة حاليًا"
        )
        return
    
    try:
        # إرسال رسالة الانتظار
        wait_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💭 جاري التفكير في رد مناسب..."
        )
        
        # طلب من API الذكاء الاصطناعي
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_URL,
                headers={'Content-Type': 'application/json'},
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            reply = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "لم أتمكن من فهم سؤالك")
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=reply
            )
            
    except httpx.RequestError as e:
        logger.error(f"خطأ في اتصال الذكاء الاصطناعي: {e}")
        ai_available = False
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ تعذر الاتصال بخدمة الذكاء الاصطناعي، يرجى المحاولة لاحقًا"
        )
    except Exception as e:
        logger.error(f"خطأ غير متوقع في الرد على الرسالة: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ حدث خطأ غير متوقع في معالجة طلبك"
        )
    finally:
        # حذف رسالة الانتظار
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=wait_msg.message_id
            )
        except:
            pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()
    
    try:
        action, url = query.data.split('_', 1)
        chat_id = query.message.chat_id
        
        if action == 'shorten':
            # تقصير الرابط
            wait_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ جاري تقصير الرابط..."
            )
            
            try:
                short_url = await shorten_url(url)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔗 الرابط المختصر:\n{short_url}"
                )
            except:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ تعذر تقصير الرابط"
                )
            finally:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=wait_msg.message_id
                )
                
        elif action == 'download':
            # تنزيل الفيديو
            await handle_video_download(url, chat_id, context)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الزر: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ حدث خطأ في معالجة طلبك"
        )
    finally:
        # حذف الرسالة الأصلية
        try:
            await query.message.delete()
        except:
            pass

async def main() -> None:
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        # إنشاء تطبيق Telegram
        application = ApplicationBuilder() \
            .token(TELEGRAM_TOKEN) \
            .build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond_to_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info("جاري تشغيل البوت...")
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"خطأ فادح في تشغيل البوت: {e}")
        raise

if __name__ == '__main__':
    # تشغيل Flask في خيط منفصل
    from threading import Thread
    flask_thread = Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False
        )
    )
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت الرئيسي
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("إيقاف البوت...")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
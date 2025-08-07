# Boot_Telegrame Smart





[Purple Modern Neon New AI Robot Video_20241107_105117_٠٠٠٠.pptx](https://github.com/user-attachments/files/21673773/Purple.Modern.Neon.New.AI.Robot.Video_20241107_105117_.pptx)














import json  # استيراد مكتبة JSON للتعامل مع البيانات بتنسيق JSON
import os  # استيراد مكتبة OS للتعامل مع نظام الملفات
import asyncio  # استيراد مكتبة asyncio للتعامل مع البرمجة غير المتزامنة
import sqlite3  # استيراد مكتبة SQLite3 للتعامل مع قاعدة بيانات SQLite
import httpx  # استيراد مكتبة httpx لإجراء طلبات HTTP غير متزامنة
import logging  # استيراد مكتبة logging لتسجيل الأخطاء والمعلومات
import nest_asyncio  # استيراد مكتبة nest_asyncio للسماح بالتشغيل المتداخل ل asyncio
from flask import Flask, request, jsonify, render_template  # استيراد مكتبات Flask لإنشاء تطبيق ويب
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # استيراد مكتبات Telegram للتعامل مع الرسائل
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes  # استيراد مكتبات Telegram لـ bot
import yt_dlp  # استيراد مكتبة yt-dlp لتنزيل الفيديوهات
import re  # استيراد مكتبة regex للتعامل مع التعبيرات العادية
from datetime import datetime  # استيراد مكتبة datetime للتعامل مع الوقت والتاريخ

# إعداد تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)

# تطبيق nest_asyncio
nest_asyncio.apply()

# إعدادات API
TELEGRAM_TOKEN = ''  # استبدل بهذا التوكن الخاص بك
API_KEY = ''  # استبدل بهذا API Key الخاص بك
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}'
previous_message_id = None

# متغير للتحكم في حالة الذكاء الاصطناعي
ai_available = True

# إنشاء تطبيق Flask
app = Flask(__name__)

# إعداد قاعدة بيانات SQLite
DB_NAME = 'bot_data.db'

def initialize_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''  # إنشاء جدول المستخدمين إذا لم يكن موجودًا
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                timestamp TEXT
            )
        ''')
        cursor.execute('''  # إنشاء جدول المستخدمين النشيطين إذا لم يكن موجودًا
            CREATE TABLE IF NOT EXISTS active_users (
                id INTEGER PRIMARY KEY
            )
        ''')
        conn.commit()

initialize_database()

@app.route('/previous_users', methods=['GET'])
def previous_users():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''  # جلب قائمة المستخدمين السابقين
            SELECT * FROM users 
            WHERE id NOT IN (SELECT DISTINCT id FROM active_users)
        ''')
        previous_users_list = cursor.fetchall()
    return render_template('previous_users.html', previous_users=previous_users_list)

@app.route('/active_users', methods=['GET'])
def active_users():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id IN (SELECT DISTINCT id FROM active_users)')  # جلب قائمة المستخدمين النشيطين
        active_users_list = cursor.fetchall()
    return render_template('active_users.html', active_users=active_users_list)

def clean_filename(filename: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # إزالة رموز غير مسموح بها
    filename = filename[:255]  # تحديد طول اسم الملف إلى 255 حرف
    return filename

async def shorten_url(long_url: str) -> str:
    url = f"https://tinyurl.com/api-create.php?url={long_url}"  # إعداد رابط تقصير URL
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # إجراء طلب GET لتقصير الرابط
        response.raise_for_status()  # رفع خطأ في حالة الاستجابة غير الناجحة
        return response.text  # إعادة الرابط المقصر

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "\U0001F31F مرحبًا بك في بوتنا! \U0001F31F\n\n"
        "يمكنك استخدام الأوامر التالية:\n"
        "- /help: للحصول على قائمة بالمساعدة.\n"
        "- أرسل لي رابطًا طويلاً لتقصيره أو لتنزيل فيديو."
    )
    await context.bot.send_message(chat_id=update.message.chat.id, text=welcome_message)  # إرسال رسالة ترحيبية

    user_id = update.message.from_user.id  # الحصول على معرف المستخدم
    username = update.message.from_user.username or "مستخدم بدون اسم"  # الحصول على اسم المستخدم
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # الحصول على الوقت الحالي

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (id, username, timestamp) VALUES (?, ?, ?)', (user_id, username, timestamp))  # إدراج المستخدم في قاعدة البيانات
        conn.commit()
    logging.info(f'User {username} (ID: {user_id}) added to the database at {timestamp}.')  # تسجيل معلومات المستخدم

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = (
        "\U0001F4AC يمكنني مساعدتك في الأمور التالية:\n"
        "- تقصير الروابط: أرسل لي رابطًا طويلًا وسأقوم بتقصيره.\n"
        "- تنزيل الفيديو: أرسل لي رابط فيديو من تيك توك، إنستغرام، أو فيسبوك.\n"
    )
    await context.bot.send_message(chat_id=update.message.chat.id, text=help_message)  # إرسال رسالة مساعدة

async def ask_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, order: str = "default") -> None:
    shortened_url = url[:50]  # تقصير الرابط لمشاهدته في الزر
    keyboard = [
        [
            InlineKeyboardButton("تقصير الرابط", callback_data=f"shorten_{shortened_url}"),
            InlineKeyboardButton("تنزيل الفيديو", callback_data=f"download_{shortened_url}"),
        ]
    ] if order == "default" else [
        [
            InlineKeyboardButton("تنزيل الفيديو", callback_data=f"download_{shortened_url}"),
            InlineKeyboardButton("تقصير الرابط", callback_data=f"shorten_{shortened_url}"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)  # إعداد لوحة المفاتيح
    await context.bot.send_message(chat_id=update.message.chat.id, text="هل ترغب في تقصير الرابط أم تنزيل الفيديو؟", reply_markup=reply_markup)  # إرسال خيارات للمستخدم

async def handle_video_download(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ydl_opts = {
        'format': 'best',  # اختيار أفضل جودة
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # إعداد مسار حفظ الفيديو
    }

    try:
        waiting_message = await context.bot.send_message(chat_id=update.chat.id, text="جاري إرسال الفيديو لك...")  # إعلام المستخدم بعملية التنزيل

        await asyncio.sleep(10)  # محاكاة الوقت المستغرق لتنزيل الفيديو
        os.makedirs('downloads', exist_ok=True)  # إنشاء مجلد التحميل إذا لم يكن موجودًا

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)  # تنزيل الفيديو
            video_file = ydl.prepare_filename(info)  # إعداد اسم الملف
            cleaned_filename = clean_filename(os.path.basename(video_file))  # تنظيف اسم الملف
            destination_path = os.path.join('downloads', cleaned_filename)  # تحديد مسار الوجهة

            if os.path.exists(destination_path):  # التحقق مما إذا كان الملف موجودًا
                base, extension = os.path.splitext(cleaned_filename)
                counter = 1
                while os.path.exists(destination_path):
                    new_filename = f"{base} ({counter}){extension}"  # إنشاء اسم جديد للملف
                    destination_path = os.path.join('downloads', new_filename)
                    counter += 1
            
            os.rename(video_file, destination_path)  # إعادة تسمية الملف

            if cleaned_filename and os.path.exists(destination_path):  # التحقق من وجود الملف
                completed_message = await context.bot.send_message(chat_id=update.chat.id, text="تم التحميل...")  # إعلام المستخدم بإكمال التنزيل
                await asyncio.sleep(2)

                await context.bot.delete_message(chat_id=update.chat.id, message_id=completed_message.message_id)  # حذف رسالة الإكمال

                with open(destination_path, 'rb') as f:
                    await context.bot.send_video(chat_id=update.chat.id, video=f)  # إرسال الفيديو للمستخدم
            else:
                await context.bot.send_message(chat_id=update.chat.id, text='لم أتمكن من تحميل الفيديو. تأكد من الرابط.')  # إعلام المستخدم بوجود خطأ
    except yt_dlp.utils.DownloadError as e:
        await context.bot.send_message(chat_id=update.chat.id, text=f'خطأ في تنزيل الفيديو: {str(e)}\nيرجى التأكد من أن الفيديو متاح.')  # معالجة خطأ أثناء التنزيل
        logging.error(f"Error downloading video: {e}")  # تسجيل الخطأ
    except Exception as e:
        logging.error(f"Unexpected error: {e}")  # تسجيل أي خطأ غير متوقع
        await context.bot.send_message(chat_id=update.chat.id, text='اعتذر عن التأخير لكن أرجو منك الانتظار من فضلك \U0001F97A...')  # إعلام المستخدم بوجود خطأ

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)  # حذف الرسالة الأصلية
    await context.bot.send_message(chat_id=update.message.chat.id, text="لانكم الافضل \U0001F970 و فرنا لكم بوت معالجة الصور قم بالضغط هنا \U0001F448 https://t.me/AIEditImagebot")  # إرسال رابط للبوت المعالج للصور

async def respond_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global previous_message_id, ai_available  # استخدام المتغيرات العالمية
    user_message = update.message.text  # الحصول على رسالة المستخدم

    if user_message.startswith('/help'):
        await help_command(update, context)  # استدعاء دالة المساعدة
        return

    if user_message.startswith("http"):
        order = "reverse" if "عكس" in user_message else "default"  # تحديد ترتيب الخيارات
        await ask_for_action(update, context, user_message, order)  # استدعاء دالة الخيارات
        return

    waiting_message = await context.bot.send_message(chat_id=update.message.chat.id, text="يرجى الانتظار...")  # إعلام المستخدم بانتظار الرد

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{user_message}"  # إعداد بيانات الطلب
                    }
                ]
            }
        ]
    }
    headers = {'Content-Type': 'application/json'}  # إعداد الهيدر للطلب

    if not ai_available:
        await context.bot.send_message(chat_id=update.message.chat.id, text="عذرًا، خدمة الذكاء الاصطناعي غير متاحة في الوقت الحالي.")  # إعلام المستخدم بعدم توفر الخدمة
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=waiting_message.message_id)  # حذف رسالة الانتظار
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(API_URL, headers=headers, data=json.dumps(data))  # إجراء طلب POST للذكاء الاصطناعي
            response.raise_for_status()  # رفع خطأ في حالة الاستجابة غير الناجحة
            response_data = response.json()  # تحويل الاستجابة إلى JSON

            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                content = response_data['candidates'][0].get('content', {})  # الحصول على المحتوى من الاستجابة
                parts = content.get('parts', [])

                if parts:
                    bot_response = parts[0].get('text', "لم أتمكن من الحصول على نص الرد.")  # الحصول على النص من الرد
                    await context.bot.send_message(chat_id=update.message.chat.id, text=bot_response)  # إرسال الرد للمستخدم
                    previous_message_id = user_message  # حفظ الرسالة السابقة
                else:
                    await context.bot.send_message(chat_id=update.message.chat.id, text="لم أتمكن من الحصول على نص الرد.")  # إعلام المستخدم بعدم الحصول على رد
            else:
                await context.bot.send_message(chat_id=update.message.chat.id, text="لم أتمكن من الحصول على رد من الخادم.")  # إعلام المستخدم بعدم الحصول على رد
    except httpx.RequestError as e:
        logging.error(f"Request error: {e}")  # تسجيل خطأ الطلب
        ai_available = False  # تعيين حالة الذكاء الاصطناعي إلى غير متاح
        await context.bot.send_message(chat_id=update.message.chat.id, text="عذرًا، خدمة الذكاء الاصطناعي غير متاحة في الوقت الحالي.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")  # تسجيل أي خطأ غير متوقع
        await context.bot.send_message(chat_id=update.message.chat.id, text="حدث خطأ غير متوقع.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=waiting_message.message_id)  # حذف رسالة الانتظار

# دالة لحذف المستخدم من جدول المستخدمين النشيطين
async def remove_user(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM active_users WHERE id = ?', (user_id,))  # حذف المستخدم من جدول المستخدمين النشيطين
        conn.commit()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query  # الحصول على استعلام الزر
    await query.answer()  # الرد على الاستعلام
    await query.message.delete()  # حذف الرسالة الأصلية

    waiting_message = await context.bot.send_message(chat_id=query.message.chat.id, text="يرجى الانتظار...")  # إعلام المستخدم بانتظار الرد

    url = query.data.split("_", 1)[1]  # استخراج الرابط من البيانات

    if query.data.startswith("shorten_"):
        try:
            temp_message = await context.bot.send_message(chat_id=query.message.chat.id, text="جاري تقصير الرابط...")  # إعلام المستخدم بعملية التقصير
            shortened_url = await shorten_url(url)  # استدعاء دالة تقصير الرابط
            await context.bot.send_message(chat_id=query.message.chat.id, text=f"الرابط المختصر: {shortened_url}")  # إرسال الرابط المقصر للمستخدم
            await context.bot.delete_message(chat_id=query.message.chat.id, message_id=temp_message.message_id)  # حذف رسالة التقصير
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat.id, text=f"حدث خطأ: {e}")  # إرسال رسالة خطأ
    
    elif query.data.startswith("download_"):
        await handle_video_download(url, query.message, context)  # استدعاء دالة تنزيل الفيديو

    await context.bot.delete_message(chat_id=query.message.chat.id, message_id=waiting_message.message_id)  # حذف رسالة الانتظار

async def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()  # إعداد تطبيق Telegram
    application.add_handler(CommandHandler("start", start))  # إضافة معالج أمر /start
    application.add_handler(CommandHandler("help", help_command))  # إضافة معالج أمر /help
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond_to_message))  # إضافة معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # إضافة معالج الصور
    application.add_handler(CallbackQueryHandler(button_handler))  # إضافة معالج استعلام الزر
    await application.run_polling()  # بدء التشغيل

if __name__ == '__main__':
    from threading import Thread  # استيراد Thread من مكتبة threading
    Thread(target=lambda: app.run(port=5000)).start()  # بدء تطبيق Flask في خيط جديد
    asyncio.run(main())  # بدء تشغيل تطبيق Telegram



                            
;                          شرح مختصر للكود

; تخزين بيانات المستخدمين:
; يستخدم قاعدة بيانات SQLite لتخزين معلومات المستخدمين مثل معرفهم، اسم المستخدم، والتوقيت.
; استيراد المكتبات الأساسية:
; Flask: لإنشاء واجهة ويب بسيطة.
; httpx: لإجراء طلبات HTTP غير متزامنة.
; yt-dlp: لتنزيل الفيديوهات من مواقع مثل يوتيوب.
; logging: لتسجيل الأخطاء والمعلومات.
; تهيئة قاعدة البيانات:
; يقوم بإنشاء جداول لتخزين بيانات المستخدمين النشطين والسابقين.
; وظائف البوت:
; /start: ترحب بالمستخدم وتعرض الأوامر المتاحة.
; /help: توضح للمستخدم كيفية استخدام البوت.
; تقصير الروابط: يمكن المستخدم من إرسال روابط طويلة لتقصيرها .
; تنزيل الفيديوهات: يستقبل روابط الفيديو ويقوم بتنزيلها وإرسالها للمستخدم.
; التعامل مع الرسائل:
; يستمع للرسائل النصية ويقرر كيفية الرد بناءً على محتوى الرسالة.
; يستخدم أزرار تفاعلية تسمح للمستخدم باختيار ما إذا كان يريد تقصير رابط أو تنزيل فيديو.
; التعامل مع الأخطاء:
; يسجل الأخطاء المختلفة مثل أخطاء الشبكة أو أخطاء أثناء تنزيل الفيديو، ويقوم بإبلاغ المستخدمين بها.
; تشغيل البوت:
; يتم تشغيل البوت باستخدام خيوط متعددة بحيث يعمل بشكل متزامن مع تطبيق Flask.

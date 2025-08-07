import telebot
import easyocr  # type: ignore
from telebot import types
from PIL import Image, ImageEnhance
import io
import time
from requests.exceptions import ConnectionError
from rembg import remove  # استيراد المكتبة لحذف الخلفية
    
bot = telebot.TeleBot("7745414776:AAG0KLjLG5zv3NJ_HoJ_gfZqWeHMfzwvwDg")  # رمز البوت الخاص بك
reader = easyocr.Reader(['ar', 'en'])  # دعم اللغتين العربية والإنجليزية

def extract_text_from_image(image_bytes):
    """استخراج النص من الصورة باستخدام EasyOCR."""
    try:
        result = reader.readtext(image_bytes, detail=0, paragraph=True)
        formatted_text = "\n".join(result)
        return format_text(formatted_text)  # تنسيق النص المستخرج
    except Exception as e:
        print(f"خطأ في استخراج النص: {str(e)}")
        return "عذرًا، لم أتمكن من استخراج النص من الصورة."

def format_text(text):
    """تنسيق النص لجعله أكبر وأفضل."""
    return f"<pre>{text}</pre>"  # استخدام تنسيق <pre> للحفاظ على التنسيق

def convert_image_to_pdf(image_bytes):
    """تحويل الصورة إلى PDF."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')

        pdf_bytes = io.BytesIO()
        image.save(pdf_bytes, format='PDF')
        pdf_bytes.seek(0)
        return pdf_bytes
    except Exception as e:
        print(f"خطأ في تحويل الصورة إلى PDF: {str(e)}")
        return "عذرًا، لم أتمكن من تحويل الصورة إلى PDF."

def enhance_image(image_bytes):
    """تحسين جودة الصورة."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(image)
        enhanced_image = enhancer.enhance(1.5)  # زيادة التباين
        output_bytes = io.BytesIO()
        enhanced_image.save(output_bytes, format='JPEG')
        output_bytes.seek(0)
        return output_bytes
    except Exception as e:
        print(f"خطأ في تحسين الصورة: {str(e)}")
        return "عذرًا، لم أتمكن من تحسين الصورة."

def convert_image_format(image_bytes, format):
    """تحويل الصورة إلى صيغة جديدة (jpg, png, etc.)."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        output_bytes = io.BytesIO()
        
        # تأكد من أن الصيغة صحيحة
        valid_formats = ['JPEG', 'PNG', 'BMP', 'GIF', 'TIFF']
        if format.upper() not in valid_formats:
            return f"خطأ: صيغة '{format}' غير صالحة. يرجى اختيار صيغة صحيحة."

        image.save(output_bytes, format=format.upper())
        output_bytes.seek(0)  # إعادة تعيين موضع المؤشر إلى البداية
        return output_bytes
    except Exception as e:
        print(f"خطأ في تحويل الصورة إلى صيغة جديدة: {str(e)}")
        return "عذرًا، حدث خطأ أثناء تحويل الصورة إلى الصيغة المطلوبة."

def change_image_color(image_bytes, color):
    """تغيير ألوان الصورة بناءً على اللون المحدد مع تنويع الألوان بشكل أكبر."""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        r, g, b = image.split()

        if color == 'red':
            image = Image.merge("RGB", (r, Image.new('L', image.size, 0), Image.new('L', image.size, 0)))  # أحمر فقط
        elif color == 'green':
            image = Image.merge("RGB", (Image.new('L', image.size, 0), g, Image.new('L', image.size, 0)))  # أخضر فقط
        elif color == 'blue':
            image = Image.merge("RGB", (Image.new('L', image.size, 0), Image.new('L', image.size, 0), b))  # أزرق فقط
        elif color == 'yellow':
            image = Image.merge("RGB", (r, r, Image.new('L', image.size, 0)))  # أصفر (أحمر + أخضر)
        elif color == 'cyan':
            image = Image.merge("RGB", (Image.new('L', image.size, 0), g, b))  # أزرق مخضر (أخضر + أزرق)
        elif color == 'magenta':
            image = Image.merge("RGB", (r, Image.new('L', image.size, 0), b))  # أرجواني (أحمر + أزرق)
        elif color == 'pink':
            image = Image.merge("RGB", (r, g, Image.new('L', image.size, 0)))  # وردي (أحمر + أخضر)
        elif color == 'brown':
            image = Image.merge("RGB", (r, Image.new('L', image.size, 0), b))  # بني (أحمر + أزرق)
        elif color == 'teal':
            image = Image.merge("RGB", (Image.new('L', image.size, 0), g, b))  # أزرق مخضر (أخضر + أزرق)

        output_bytes = io.BytesIO()
        image.save(output_bytes, format='JPEG')
        output_bytes.seek(0)
        return output_bytes
    except Exception as e:
        print(f"خطأ في تغيير ألوان الصورة: {str(e)}")
        return "عذرًا، لم أتمكن من تغيير ألوان الصورة."

def remove_background(image_bytes):
    """حذف خلفية الصورة وإرجاع الصورة بدون خلفية."""
    try:
        output = remove(image_bytes)
        return io.BytesIO(output)
    except Exception as e:
        print(f"خطأ في حذف الخلفية: {str(e)}")
        return "عذرًا، لم أتمكن من حذف الخلفية."

def create_color_options_markup():
    """إنشاء أزرار عائمة لتحديد ألوان الصورة."""
    markup = types.InlineKeyboardMarkup()
    colors = [
        'red', 'green', 'blue', 'yellow',
        'cyan', 'magenta', 'pink', 'brown', 'teal'
    ]
    
    for i in range(0, len(colors), 4):
        markup.add(*[types.InlineKeyboardButton(color.capitalize(), callback_data=f'change_color_{color}') for color in colors[i:i+4]])
    
    return markup

def create_format_options_markup():
    """إنشاء أزرار عائمة لتحديد صيغة الصورة."""
    markup = types.InlineKeyboardMarkup()
    formats = ['jpg', 'png', 'bmp', 'gif', 'tiff']
    for fmt in formats:
        markup.add(types.InlineKeyboardButton(fmt.upper(), callback_data=f'convert_to_{fmt}'))
    return markup

def create_options_markup():
    """إنشاء أزرار عائمة (Inline) للخيارات المتاحة بعد إرسال الصورة."""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('📄تحويل إلى PDF', callback_data='convert_to_pdf')
    btn2 = types.InlineKeyboardButton('🖼️صيغة جديدة', callback_data='convert_image_format')
    btn3 = types.InlineKeyboardButton('📝استخراج النص', callback_data='extract_text')
    btn4 = types.InlineKeyboardButton('🎨تغيير الالوان ', callback_data='change_image_color')
    btn5 = types.InlineKeyboardButton('🗑️حذف الخلفية', callback_data='remove_background')  # زر حذف الخلفية
    btn6 = types.InlineKeyboardButton('✨تحسين الصورة', callback_data='enhance_image')  # زر تحسين الصورة
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحبًا بك في خدمة معالجة الصور! أرسل صورة لتحصل على خيارات المعالجة المتاحة.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        waiting_message = bot.reply_to(message, "يرجى الانتظار، يتم معالجة الصورة...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        if not downloaded_file or len(downloaded_file) == 0:
            error_message = bot.reply_to(message, "لم أتمكن من تحميل الصورة أو الصورة فارغة. يرجى المحاولة مرة أخرى.")
            time.sleep(5)
            bot.delete_message(message.chat.id, error_message.message_id)
            return

        markup = create_options_markup()
        bot.send_message(message.chat.id, "اختر الخيار الذي تريده:", reply_markup=markup)

        bot.user_data[message.chat.id] = {
            'downloaded_file': downloaded_file,
            'waiting_message_id': waiting_message.message_id
        }
    except Exception as e:
        error_message = bot.reply_to(message, "عذرًا، حدث خطأ أثناء معالجة الصورة. يرجى المحاولة لاحقًا.")
        time.sleep(5)
        bot.delete_message(message.chat.id, error_message.message_id)
        print(f"خطأ: {str(e)}")  # طباعة تفاصيل الخطأ

@bot.callback_query_handler(func=lambda call: True)
def process_option(call):
    user_data = bot.user_data.get(call.message.chat.id, {})
    downloaded_file = user_data.get('downloaded_file')
    waiting_message_id = user_data.get('waiting_message_id')

    if waiting_message_id:
        try:
            bot.delete_message(call.message.chat.id, waiting_message_id)
        except telebot.apihelper.ApiTelegramException:
            pass

    if downloaded_file:
        try:
            if call.data == 'convert_to_pdf':
                pdf_bytes = convert_image_to_pdf(downloaded_file)
                if pdf_bytes and pdf_bytes.getbuffer().nbytes > 0:
                    send_document_with_retry(call.message.chat.id, pdf_bytes, "إليك الصورة في صيغة PDF.")
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، لم أتمكن من تحويل الصورة إلى PDF.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

            elif call.data == 'convert_image_format':
                markup = create_format_options_markup()
                bot.send_message(call.message.chat.id, "اختر صيغة الصورة:", reply_markup=markup)

            elif call.data == 'extract_text':
                extracted_text = extract_text_from_image(downloaded_file)
                if extracted_text:
                    bot.reply_to(call.message, f"تم استخراج النص:\n\n{extracted_text}", parse_mode='HTML')
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، لم أتمكن من استخراج النص من الصورة.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

            elif call.data == 'change_image_color':
                markup = create_color_options_markup()
                bot.send_message(call.message.chat.id, "اختر اللون الذي تريده:", reply_markup=markup)

            elif call.data.startswith('change_color_'):
                color = call.data.split('_')[-1]
                colored_image = change_image_color(downloaded_file, color)
                if colored_image and colored_image.getbuffer().nbytes > 0:
                    send_photo_with_retry(call.message.chat.id, colored_image, f"إليك الصورة باللون {color}.")
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، لم أتمكن من تغيير لون الصورة.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

            elif call.data == 'remove_background':
                background_removed_image = remove_background(downloaded_file)
                if background_removed_image and background_removed_image.getbuffer().nbytes > 0:
                    bot.send_photo(call.message.chat.id, background_removed_image, "إليك الصورة بعد حذف الخلفية.")
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، لم أتمكن من حذف الخلفية.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

            elif call.data == 'enhance_image':
                enhanced_image = enhance_image(downloaded_file)
                if enhanced_image and enhanced_image.getbuffer().nbytes > 0:
                    send_photo_with_retry(call.message.chat.id, enhanced_image, "إليك الصورة بعد تحسين الجودة.")
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، لم أتمكن من تحسين الصورة.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

            elif call.data.startswith('convert_to_'):
                format = call.data.split('_')[-1]
                converted_image = convert_image_format(downloaded_file, format)
                if isinstance(converted_image, str):  # إذا كانت رسالة خطأ
                    error_message = bot.reply_to(call.message, converted_image)
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)
                elif converted_image and converted_image.getbuffer().nbytes > 0:
                    send_photo_with_retry(call.message.chat.id, converted_image, f"إليك الصورة بصيغة {format}.")
                else:
                    error_message = bot.reply_to(call.message, "عذرًا، فشل تحويل الصورة: الصورة الناتجة فارغة.")
                    time.sleep(5)
                    bot.delete_message(call.message.chat.id, error_message.message_id)

        except Exception as e:
            error_message = bot.reply_to(call.message, "عذرًا، حدث خطأ أثناء معالجة الخيار. يرجى المحاولة لاحقًا.")
            time.sleep(5)
            bot.delete_message(call.message.chat.id, error_message.message_id)
            print(f"تفاصيل الخطأ: {str(e)}")

    else:
        error_message = bot.reply_to(call.message, "لم أتمكن من العثور على الصورة.")
        time.sleep(5)
        bot.delete_message(call.message.chat.id, error_message.message_id)

def send_document_with_retry(chat_id, document, caption, retries=3):
    """إرسال مستند مع إعادة المحاولة في حال حدوث خطأ."""
    for attempt in range(retries):
        try:
            if document.getbuffer().nbytes > 0:
                bot.send_document(chat_id, document, caption=caption)
                return
            else:
                print("المستند فارغ، لا يمكن إرساله.")
                error_message = bot.reply_to(chat_id, "عذرًا، فشل إرسال المستند: الملف فارغ.")
                time.sleep(5)
                bot.delete_message(chat_id, error_message.message_id)
                return
        except ConnectionError:
            print(f"خطأ في الاتصال. إعادة المحاولة {attempt + 1}/{retries}...")
            time.sleep(2)
    error_message = bot.reply_to(chat_id, "عذرًا، فشل إرسال المستند بعد عدة محاولات.")
    time.sleep(5)
    bot.delete_message(chat_id, error_message.message_id)

def send_photo_with_retry(chat_id, photo, caption, retries=3):
    """إرسال صورة مع إعادة المحاولة في حال حدوث خطأ."""    
    for attempt in range(retries):
        try:
            if photo.getbuffer().nbytes > 0:
                bot.send_photo(chat_id, photo, caption=caption)
                return
            else:
                print("الصورة فارغة، لا يمكن إرسالها.")
                error_message = bot.reply_to(chat_id, "عذرًا، فشل إرسال الصورة: الصورة فارغة.")
                time.sleep(5)
                bot.delete_message(chat_id, error_message.message_id)
                return
        except ConnectionError:
            print(f"خطأ في الاتصال. إعادة المحاولة {attempt + 1}/{retries}...")
            time.sleep(2)
    error_message = bot.reply_to(chat_id, "عذرًا، فشل إرسال الصورة بعد عدة محاولات.")
    time.sleep(5)
    bot.delete_message(chat_id, error_message.message_id)

# بدء البوت
if __name__ == '__main__':
    bot.user_data = {}  # استخدام قاموس لتخزين بيانات المستخدم
    bot.polling(none_stop=True, timeout=30)
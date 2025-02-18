from telegram import Update, InputSticker
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image, UnidentifiedImageError
import os
import re
import json

# حفظ الحزم في ملف JSON
def save_pack(pack_name, stickers):
    if os.path.exists('sticker_packs.json'):
        with open('sticker_packs.json', 'r') as f:
            data = json.load(f)
    else:
        data = {}

    data[pack_name] = stickers

    with open('sticker_packs.json', 'w') as f:
        json.dump(data, f, indent=4)

# تعريف الأمر /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('مرحبًا! أنا بوت لإنشاء حزم الملصقات. استخدم الأمر /newpack لبدء إنشاء حزمة جديدة.')

# تعريف الأمر /newpack
async def newpack(update: Update, context: CallbackContext):
    await update.message.reply_text("أرسل لي اسم الحزمة الجديدة.")
    context.user_data['awaiting_pack_name'] = True

# تعديل وظيفة تنسيق اسم الحزمة لدعم الرموز بشكل صحيح
def format_pack_name(pack_name: str) -> str:
    # إزالة مساحات غير ضرورية من البداية والنهاية
    pack_name = pack_name.strip()
    if not pack_name:
        raise ValueError("اسم الحزمة لا يمكن أن يكون فارغًا.")
    
    # استبدال الرموز غير المدعومة مثل "@" ب "_" أو حذفها
    valid_name = re.sub(r'[^\w\s\-#&*.,;:|_+=?%(){}<>/]', '', pack_name)  # الاحتفاظ ببعض الرموز
    valid_name = valid_name.replace('@', '_')  # استبدال "@" برمز مقبول
    return valid_name

# وظيفة لتعديل أبعاد الصورة
def resize_sticker(file_path: str):
    try:
        with Image.open(file_path) as img:
            # ضبط الحجم إلى 512x512 مع الحفاظ على نسبة العرض إلى الارتفاع
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            img.save(file_path, format="WEBP")
    except UnidentifiedImageError:
        raise ValueError("الملف الذي تم تنزيله ليس صورة صالحة.")

# معالجة الرسائل النصية
async def handle_text(update: Update, context: CallbackContext):
    if context.user_data.get('awaiting_pack_name'):
        raw_pack_name = update.message.text.strip()
        try:
            pack_name = format_pack_name(raw_pack_name)
            context.user_data['pack_name'] = pack_name
            context.user_data['awaiting_pack_name'] = False
            await update.message.reply_text(f"تم تعيين اسم الحزمة إلى: {pack_name}. أرسل لي الملصقات الآن.")
        except ValueError as e:
            await update.message.reply_text(f"حدث خطأ: {e}")
    else:
        await update.message.reply_text("لا أفهم الرسالة. استخدم /newpack لبدء إنشاء حزمة.")

# معالجة الملصقات
async def handle_sticker(update: Update, context: CallbackContext):
    sticker = update.message.sticker
    pack_name = context.user_data.get('pack_name')

    if not pack_name:
        await update.message.reply_text("الرجاء تعيين اسم الحزمة أولاً باستخدام الأمر /newpack.")
        return

    try:
        # تنزيل الملصق
        file = await context.bot.get_file(sticker.file_id)
        file_path = f"{sticker.file_id}.webp"
        await file.download_to_drive(file_path)

        # تحقق من نوع الملصق
        if sticker.is_animated or sticker.is_video:
            # دعم الملصقات المتحركة
            format_sticker = InputSticker(
                sticker=open(file_path, 'rb'),
                emoji_list=["👍"],
                format="animated" if sticker.is_animated else "video"
            )
        else:
            # دعم الملصقات الثابتة
            resize_sticker(file_path)
            format_sticker = InputSticker(
                sticker=open(file_path, 'rb'),
                emoji_list=["👍"],
                format="static"
            )

        # إضافة الملصق إلى الحزمة
        await context.bot.create_new_sticker_set(
            user_id=update.message.from_user.id,
            name=pack_name,
            title=pack_name.replace('_', ' '),
            stickers=[format_sticker]
        )

        # حفظ الحزمة
        save_pack(pack_name, [sticker.file_id])

        # رابط الحزمة
        pack_link = f"https://t.me/addstickers/{pack_name}"
        await update.message.reply_text(f"تمت إضافة الملصق إلى الحزمة: {pack_name}\nرابط الحزمة: {pack_link}")
    except ValueError as e:
        await update.message.reply_text(f"حدث خطأ: {e}")
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء إضافة الملصق: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    BOT_TOKEN = "7545852425:AAEYJO6SOy5xlHC6xjdtCRtwKl4a0uCmNME"
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newpack", newpack))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    application.run_polling()

if __name__ == '__main__':
    main()
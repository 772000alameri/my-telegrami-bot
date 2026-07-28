import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------------------------------------------------
# 1. إعدادات البوت الأساسية (قم بتغيير البيانات هنا)
# -------------------------------------------------------------
BOT_TOKEN = "8657190972:AAENB8tBQE5RwEaEYgH4WdPnnTeNkCj3CiI"
ADMIN_ID = 8556190240  # أصلح هذا واكتب ID أدمين البوت (يمكنك معرفته من بوت @userinfobot)
CHANNEL_USERNAME = "@OrUK4YwY9ig2NmZksexse18"  # معرف قناتك مع العلامة @ للتحقق من الاشتراك
# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# -------------------------------------------------------------
# 2. إعداد قاعدة البيانات (SQLite)
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    # جدول المستخدمين ونظام الإحالة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referred_by INTEGER,
            points INTEGER DEFAULT 0
        )
    ''')
    # جدول الردود التلقائية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auto_responses (
            keyword TEXT PRIMARY KEY,
            response TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------
# 3. دالة التحقق من اشتراك القناة
# -------------------------------------------------------------
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception:
        return False

# -------------------------------------------------------------
# 4. لوحة التحكم والأزرار الشفافة
# -------------------------------------------------------------
def get_main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🔗 رابط الإحالة الخاص بي", callback_data="ref_link")],
        [InlineKeyboardButton("📊 إحصائياتي ونقاطي", callback_data="my_stats")],
        [InlineKeyboardButton("📢 القناة الرسمية", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الأدمن", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

# -------------------------------------------------------------
# 5. معالجة أمر البداية /start ورسالة الترحيب
# -------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    # فحص الاشتراك الإجباري أولاً
    subscribed = await check_subscription(user_id, context)
    if not subscribed:
        join_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("اشترك في القناة أولاً 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("تحقق من الاشتراك 🔄", callback_data="check_sub")]
        ])
        await update.message.reply_text(
            f"مرحباً بك يا {first_name}! 👋\n\nلاستخدام البوت والاستفادة من خدماته، يرجى الاشتراك في قناتنا أولاً ثم الضغط على زر التحقق.",
            reply_markup=join_btn
        )
        return

    # تسجيل المستخدم وتسجيل الإحالة
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if not existing_user:
        referred_by = None
        if context.args and context.args[0].isdigit():
            ref_id = int(context.args[0])
            if ref_id != user_id:
                referred_by = ref_id
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (ref_id,))
        
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referred_by))
        conn.commit()

    conn.close()

    welcome_msg = f"مرحباً بك يا {first_name} في البوت الاحترافي! 🤖\nاختر من القائمة أدناه ما تريد القيام به:"
    await update.message.reply_text(welcome_msg, reply_markup=get_main_keyboard(user_id == ADMIN_ID))

# -------------------------------------------------------------
# 6. معالجة الأزرار التفاعلية (Callback Queries)
# -------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_sub":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ تم التحقق من اشتراكك بنجاح! أرسل /start لبدء الاستخدام.")
        else:
            await query.answer("❌ لم تشترك في القناة بعد!", show_alert=True)

    elif query.data == "ref_link":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        msg = f"🔗 رابط الإحالة الخاص بك:\n`{link}`\n\nقم بنشره! كل شخص يشترك عن طريقك يمنحك نقطة واحدة لزيادة تفاعلك ودعم القناة."
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif query.data == "my_stats":
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        pts = res[0] if res else 0
        conn.close()
        await query.message.reply_text(f"📊 إحصائياتك:\nعدد الأشخاص الذين دعوتهم: {pts}")

    elif query.data == "admin_panel" and user_id == ADMIN_ID:
        admin_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 إحصائيات البوت العامة", callback_data="global_stats")],
            [InlineKeyboardButton("➕ إضافة رد تلقائي", callback_data="add_response_help")]
        ])
        await query.message.reply_text("⚙️ **لوحة تحكم الأدمن:**", reply_markup=admin_markup, parse_mode="Markdown")

    elif query.data == "global_stats" and user_id == ADMIN_ID:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        conn.close()
        await query.message.reply_text(f"🌐 إجمالي مستخدمي البوت: {total_users} مستخدم.")

    elif query.data == "add_response_help" and user_id == ADMIN_ID:
        await query.message.reply_text("لإضافة رد تلقائي جديد، أرسل رسالة بالشكل التالي:\n`أضف [الكلمة] [الرد]`\n\nمثال:\n`أضف السلام عليكم وعليكم السلام ورحمة الله وبركاته`", parse_mode="Markdown")

# -------------------------------------------------------------
# 7. إدارة الردود التلقائية ورسائل الأدمن
# -------------------------------------------------------------
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # إضافة رد تلقائي من قبل الأدمن
    if user_id == ADMIN_ID and text.startswith("أضف "):
        parts = text.split(" ", 2)
        if len(parts) == 3:
            keyword, response = parts[1], parts[2]
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO auto_responses (keyword, response) VALUES (?, ?)", (keyword, response))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ تم إضافة الرد التلقائي للكلمة: ({keyword})")
            return

    # البحث عن رد تلقائي في قاعدة البيانات
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT response FROM auto_responses WHERE keyword = ?", (text,))
    res = cursor.fetchone()
    conn.close()

    if res:
        await update.message.reply_text(res[0])

# -------------------------------------------------------------
# 8. التشغيل الرئيسي للبوت
# -------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("🤖 البوت يعمل الان بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()

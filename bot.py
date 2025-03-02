import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# 配置信息
BOT_TOKEN = "7599294205:AAEUZe_Yz24wAW4BsN1pB3Ad1-j7rEGRcv4"
ADMIN_ID = 7628464820
DB_NAME = "bot_database.db"

# 初始化数据库
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS monitored_channels
               (channel_id TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS keyword_mappings
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                match_type TEXT,
                group_id TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS auth_users
               (user_id TEXT PRIMARY KEY)''')
cursor.execute(f"INSERT OR IGNORE INTO auth_users VALUES ('{ADMIN_ID}')")
conn.commit()

# 日志配置
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def auth_check(user_id):
    cursor.execute("SELECT 1 FROM auth_users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_check(update.effective_user.id):
        return
    keyboard = [
        [InlineKeyboardButton("📡 监控频道管理", callback_data='manage_monitor')],
        [InlineKeyboardButton("🔑 关键词设置", callback_data='manage_keywords'),
         InlineKeyboardButton("📊 数据统计", callback_data='stats')],
        [InlineKeyboardButton("📖 使用指南", callback_data='help')]
    ]
    await update.message.reply_text(
        "🏮 频道监控机器人控制面板 🏮\n请选择操作：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        cursor.execute("SELECT keyword, match_type, group_id FROM keyword_mappings")
        mappings = cursor.fetchall()
        for keyword, match_type, group_id in mappings:
            content = update.channel_post.text.lower()
            if (
                (match_type == "精准" and keyword.lower() == content) or
                (match_type == "模糊" and keyword.lower() in content)
            ):
                await context.bot.send_message(
                    chat_id=group_id,
                    text=f"🔔 检测到关键词匹配\n来源频道：{update.channel_post.chat.title}\n匹配内容：\n{update.channel_post.text}"
                )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not await auth_check(user_id):
        return

    if query.data == 'manage_monitor':
        await manage_monitor(query)
    elif query.data == 'manage_keywords':
        await manage_keywords(query)
    elif query.data == 'help':
        await show_help(query)

async def manage_monitor(query):
    keyboard = [
        [InlineKeyboardButton("➕ 添加监控频道", callback_data='add_channel')],
        [InlineKeyboardButton("➖ 移除监控频道", callback_data='remove_channel')],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
    ]
    await query.edit_message_text(
        "📡 频道监控管理\n当前监控中的频道：\n" + 
        "\n".join([f"• {row[0]}" for row in cursor.execute("SELECT channel_id FROM monitored_channels")]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def manage_keywords(query):
    keyboard = [
        [InlineKeyboardButton("➕ 新增关键词绑定", callback_data='add_keyword')],
        [InlineKeyboardButton("➖ 删除关键词绑定", callback_data='remove_keyword')],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
    ]
    await query.edit_message_text(
        "🔑 关键词绑定管理\n当前生效规则：\n" +
        "\n".join([f"• {row[0]} ({row[1]}) → {row[2]}" 
                  for row in cursor.execute("SELECT keyword, match_type, group_id FROM keyword_mappings")]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help(query):
    help_text = """
    📖 使用指南
    
    1. 添加监控频道：
    - 将机器人设为频道管理员
    - 在控制面板选择添加监控
    
    2. 设置关键词规则：
    - 选择关键词类型（精准/模糊）
    - 输入目标群组ID
    
    3. 数据统计：
    - 查看消息处理量
    - 查看匹配成功率
    
    4. 权限管理：
    - 仅授权用户可操作
    """
    await query.edit_message_text(help_text, 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data='main_menu')]]))

if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_message))
    
    application.run_polling()

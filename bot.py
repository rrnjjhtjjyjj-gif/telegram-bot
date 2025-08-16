import os
import requests
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
from datetime import datetime

# إعدادات البوت من الـ Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# تهيئة البوت
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# تفعيل اللوج
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# متغيرات التخزين
users_data = {
    "subscribed": set(),
    "activation_attempts": 0,
    "successful_activations": 0
}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    users_data["activation_attempts"] += 1
    
    if not check_subscription(user.id):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👋 مرحبًا {user.first_name}\n\n🔔 يجب الاشتراك في قناتنا أولاً:\n{CHANNEL_ID}\nثم أرسل /start مرة أخرى"
        )
        return
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"مرحبًا بك {user.first_name} 🌟\n\n📱 أرسل رقم الهاتف وكلمة السر بهذا الشكل:\nالرقم:الباسورد"
    )

def handle_activation(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if not check_subscription(user.id):
        update.message.reply_text("⚠️ يجب الاشتراك في القناة أولاً!")
        return
    
    try:
        phone, password = update.message.text.split(":")
        user_info = {
            "phone": phone.strip(),
            "password": password.strip(),
            "username": user.username,
            "user_id": user.id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        result = activate_offer(user_info)
        
        update.message.reply_text(result["message"])
        
        if result["success"]:
            users_data["successful_activations"] += 1
            bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ تفعيل ناجح\n\n📱 الرقم: {user_info['phone']}\n👤 اليوزر: @{user_info['username']}\n\nالنتيجة: {result['message']}"
            )
        else:
            bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ تفعيل فاشل\n\n📱 الرقم: {user_info['phone']}\n👤 اليوزر: @{user_info['username']}\n\nالخطأ: {result['message']}"
            )
            
    except Exception as e:
        update.message.reply_text(f"⚠️ خطأ في الإدخال! يرجى استخدام الصيغة الصحيحة:\nالرقم:الباسورد\n\nError: {str(e)}")

def activate_offer(user_data):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13)',
            'Accept': 'application/json'
        }
        
        payload = {
            'msisdn': user_data["phone"],
            'lang': "ar",
            'password': user_data["password"]
        }
        
        response = requests.post(
            "https://api.meridagame.com/api/speedRedeemOffer",
            data=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "errDesc" in str(result):
                return {
                    "success": False,
                    "message": f"⚠️ {result.get('data', {}).get('redeemOutputs', {}).get('RedeemErrorDoc', {}).get('errDesc', 'فشل التفعيل')}"
                }
            return {
                "success": True,
                "message": f"🎉 تم التفعيل بنجاح!\n{result}"
            }
        return {
            "success": False,
            "message": f"🔴 خطأ في السيرفر: {response.status_code}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"🚫 خطأ في الاتصال: {str(e)}"
        }

def get_stats(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
        
    stats_msg = f"""
📊 إحصائيات البوت:

🔢 إجمالي المحاولات: {users_data['activation_attempts']}
✅ التفعيلات الناجحة: {users_data['successful_activations']}
📈 نسبة النجاح: {round((users_data['successful_activations']/users_data['activation_attempts'])*100 if users_data['activation_attempts'] > 0 else 0, 2)}%
"""
    context.bot.send_message(chat_id=ADMIN_ID, text=stats_msg)

# إضافة الأوامر
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("stats", get_stats))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_activation))

# بدء البوت
updater.start_polling()
print("🤖 البوت يعمل الآن...")
updater.idle()

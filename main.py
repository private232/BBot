import json
import os
import time
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# ملف تخزين البيانات
DATA_FILE = "bank_data.json"
GROUPS_FILE = "groups_data.json"
COOLDOWN_TIME = 900  # 15 دقيقة بالثواني
SAME_BANK_TAX = 0.07  # ضريبة التحويل لنفس البنك
DIFFERENT_BANK_TAX = 0.15  # ضريبة التحويل لبنك مختلف
SALARY_COOLDOWN = 600  # 10 دقائق بالثواني
ADMIN_ID = 1842883902  # استبدل هذا برقم ID الخاص بك كمشرف للبوت

# تحميل البيانات
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as file:
        users = json.load(file)
else:
    users = {}

if os.path.exists(GROUPS_FILE):
    with open(GROUPS_FILE, "r") as file:
        groups = json.load(file)
else:
    groups = {}


def save_data():
    with open(DATA_FILE, "w") as file:
        json.dump(users, file, indent=4, default=str)
    with open(GROUPS_FILE, "w") as file:
        json.dump(groups, file, indent=4)


# التحقق من أن الدردشة هي مجموعة
def is_group_chat(update: Update) -> bool:
    return update.effective_chat.type in ["group", "supergroup"]


# قائمة البنوك المتاحة
BANKS = {
    "الاهلي": "🏦",
    "الرافدين": "🏛️",
    "الخليج": "🌊",
    "العربي": "🕌",
    "الدولي": "🌍",
    "التجاري": "💼"
}

# قائمة الوظائف ورواتبها
JOBS = {
    "مهندس 🛠️": 3000,
    "طبيب 🩺": 3500,
    "مدرس 📚": 2000,
    "مبرمج 💻": 3200,
    "تاجر 💰": 2800,
    "طيار ✈️": 4000,
    "شرطي 👮": 2500,
    "نادل 🍽️": 1800,
    "سائق 🚗": 2000,
    "مزارع 🌾": 1500,
    "محامي ⚖️": 3000,
    "ممرض 💉": 2200,
    "مهندس معماري 🏛️": 3300,
    "صحفي 📰": 2400,
    "عالم 🔬": 3800,
    "مغني 🎤": 2700,
    "لاعب كرة قدم ⚽": 5000,
    "سباك 🔧": 1900,
    "كهربائي ⚡": 2100,
    "رسام 🎨": 2300
}

# قاموس العواصم
capitals = {
    "السعودية": "الرياض",
    "مصر": "القاهرة",
    "الجزائر": "الجزائر",
    "المغرب": "الرباط",
    "العراق": "بغداد",
    "سوريا": "دمشق",
    "تونس": "تونس",
    "الاردن": "عمان",
    "الإمارات": "ابو ظبي",
    "الكويت": "الكويت",
    "قطر": "الدوحة",
    "عمان": "مسقط",
    "لبنان": "بيروت",
    "ليبيا": "طرابلس",
    "السودان": "الخرطوم",
    "اليمن": "صنعاء",
    "الصومال": "مقديشو",
    "موريتانيا": "نواكشوط",
    "جيبوتي": "جيبوتي",
    "جزر القمر": "موروني",
    "فلسطين": "القدس",
    "البحرين": "المنامة"
}


# أوامر البوت
async def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username

    # إذا كان المستخدم هو المشرف ويتحدث مع البوت مباشرة
    if update.effective_user.id == ADMIN_ID and not is_group_chat(update):
        await show_admin_panel(update, context)
        return

    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        # عرض قائمة البنوك للمستخدم الجديد
        banks_list = "\n".join([f"{emoji} {name}" for name, emoji in BANKS.items()])
        await update.message.reply_text(
            "🏦 مرحبًا! يرجى اختيار البنك الذي تريد فتح حسابك فيه:\n\n"
            f"{banks_list}\n\n"
            "اكتب اسم البنك الذي تريده (مثال: الأهلي)"
        )
        context.user_data["awaiting_bank_choice"] = True

        # تسجيل المجموعة إذا لم تكن مسجلة
        chat_id = str(update.effective_chat.id)
        if chat_id not in groups:
            groups[chat_id] = {
                "title": update.effective_chat.title,
                "members": {}
            }
            save_data()
    else:
        await update.message.reply_text("✅ لديك حساب بالفعل.")


async def show_admin_panel(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📋 قائمة المجموعات", callback_data='groups_list')],
        [InlineKeyboardButton("💰 إرسال أموال لمجموعة", callback_data='send_money_group')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "👑 لوحة تحكم المشرف",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "👑 لوحة تحكم المشرف",
            reply_markup=reply_markup
        )


async def admin_groups_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # تحديث بيانات المجموعات من ملف البيانات
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r") as file:
            global groups
            groups = json.load(file)

    if not groups:
        await query.edit_message_text("⚠️ لا توجد مجموعات مسجلة بعد")
        return

    keyboard = []
    for chat_id, group_data in groups.items():
        keyboard.append([InlineKeyboardButton(
            f"{group_data['title']} (أعضاء: {len(group_data.get('members', {}))})",
            callback_data=f'group_{chat_id}'
        )])

    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_back')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📋 قائمة المجموعات:",
        reply_markup=reply_markup
    )


async def admin_group_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    chat_id = query.data.split('_')[1]
    group_data = groups.get(chat_id, {})

    if not group_data:
        await query.edit_message_text("⚠️ لم يتم العثور على بيانات المجموعة")
        return

    members = group_data.get('members', {})
    if not members:
        await query.edit_message_text(f"ℹ️ لا يوجد أعضاء مسجلين في {group_data['title']}")
        return

    keyboard = []
    for user_id, username in members.items():
        user_balance = users.get(user_id, {}).get('balance', 0)
        keyboard.append([InlineKeyboardButton(
            f"@{username} (ID: {user_id}) - {user_balance}$",
            callback_data=f'member_{chat_id}_{user_id}'
        )])

    keyboard.append([
        InlineKeyboardButton("💸 إرسال أموال للجميع", callback_data=f'send_all_{chat_id}'),
        InlineKeyboardButton("🔙 رجوع", callback_data='groups_list')
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"👥 أعضاء {group_data['title']}:",
        reply_markup=reply_markup
    )


async def admin_member_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    _, chat_id, user_id = query.data.split('_')
    user_data = users.get(user_id, {})

    if not user_data:
        await query.edit_message_text("⚠️ لم يتم العثور على بيانات العضو")
        return

    group_title = groups.get(chat_id, {}).get('title', 'غير معروف')
    bank_emoji = BANKS.get(user_data.get('bank', ''), '')

    keyboard = [
        [InlineKeyboardButton("💸 إرسال أموال", callback_data=f'send_{user_id}')],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f'group_{chat_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"👤 معلومات العضو:\n\n"
        f"🆔 الآيدي: {user_id}\n"
        f"🏷️ المعرف: @{user_data.get('username', 'غير معروف')}\n"
        f"🏦 البنك: {bank_emoji} {user_data.get('bank', 'غير محدد')}\n"
        f"💰 الرصيد: {user_data.get('balance', 0)}$\n"
        f"💼 الوظيفة: {user_data.get('current_job', 'لا يوجد')}\n"
        f"📌 المجموعة: {group_title}",
        reply_markup=reply_markup
    )


async def admin_send_money(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('send_all_'):
        chat_id = query.data.split('_')[2]
        context.user_data['admin_action'] = 'send_all'
        context.user_data['admin_chat_id'] = chat_id
        await query.edit_message_text(
            f"💰 الرجاء إرسال المبلغ الذي تريد إرساله لجميع أعضاء المجموعة (يمكنك استخدام قيم سالبة):\n"
            "مثال: -1000"
        )
        return

    if query.data.startswith('send_'):
        user_id = query.data.split('_')[1]
        context.user_data['admin_receiver_id'] = user_id
        context.user_data['admin_action'] = 'send_money_specific'
        await query.edit_message_text(
            f"💰 الرجاء إرسال المبلغ الذي تريد إرساله للعضو {user_id} (يمكنك استخدام قيم سالبة):\n"
            "مثال: -500"
        )
        return

    if query.data == 'send_money_group':
        await admin_groups_list(update, context)
        context.user_data['admin_action'] = 'send_money_group'
        return


async def handle_admin_message(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get('admin_action'):
        return

    text = update.message.text.strip()

    if context.user_data['admin_action'] == 'send_money_specific':
        try:
            amount = int(text)
            receiver_id = context.user_data.get('admin_receiver_id')
            if not receiver_id:
                await update.message.reply_text("⚠️ حدث خطأ، الرجاء المحاولة مرة أخرى")
                return

            if receiver_id not in users:
                await update.message.reply_text("⚠️ العضو المحدد ليس لديه حساب بنكي")
                return

            users[receiver_id]['balance'] += amount
            save_data()

            action = "إضافة" if amount >= 0 else "خصم"
            await update.message.reply_text(
                f"✅ تم {action} {abs(amount)}$ إلى العضو {receiver_id}\n"
                f"💰 رصيده الجديد: {users[receiver_id]['balance']}$"
            )

            context.user_data['admin_action'] = None
            context.user_data['admin_receiver_id'] = None

        except ValueError:
            await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا")
            return

    elif context.user_data['admin_action'] == 'send_all':
        try:
            amount = int(text)
            chat_id = context.user_data.get('admin_chat_id')
            if not chat_id:
                await update.message.reply_text("⚠️ حدث خطأ، الرجاء المحاولة مرة أخرى")
                return

            group_data = groups.get(chat_id, {})
            members = group_data.get('members', {})

            if not members:
                await update.message.reply_text("⚠️ لا يوجد أعضاء في هذه المجموعة")
                return

            count = 0
            for user_id in members:
                if user_id in users:
                    users[user_id]['balance'] += amount
                    count += 1

            save_data()

            action = "إضافة" if amount >= 0 else "خصم"
            await update.message.reply_text(
                f"✅ تم {action} {abs(amount)}$ إلى {count} عضو في {group_data.get('title', 'المجموعة')}\n"
                f"💰 تمت العملية بنجاح"
            )

            context.user_data['admin_action'] = None
            context.user_data['admin_chat_id'] = None

        except ValueError:
            await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا")
            return

    elif context.user_data['admin_action'] == 'send_money_group':
        pass


async def handle_bank_choice(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    chosen_bank = update.message.text.strip()

    if chosen_bank not in BANKS:
        await update.message.reply_text("⚠️ اسم البنك غير صحيح، يرجى اختيار بنك من القائمة:")
        banks_list = "\n".join([f"{emoji} {name}" for name, emoji in BANKS.items()])
        await update.message.reply_text(banks_list)
        return

    users[user_id] = {
        "balance": 1000,
        "bank": chosen_bank,
        "last_invest": None,
        "last_trade": None,
        "last_salary": None,
        "current_job": None,
        "capitals_answered": [],
        "username": update.effective_user.username
    }

    # تسجيل العضو في المجموعة
    chat_id = str(update.effective_chat.id)
    if chat_id in groups:
        groups[chat_id]['members'][user_id] = update.effective_user.username

    save_data()

    await update.message.reply_text(
        f"🎉 تم إنشاء حسابك البنكي في بنك {BANKS[chosen_bank]} {chosen_bank} برصيد 1000$\n"
        f"🆔 رقم حسابك: {user_id}\n"
        f"💼 يمكنك الآن استخدام الأوامر التالية:\n"
        f"• رصيدي - لعرض رصيدك\n"
        f"• استثمار - للاستثمار\n"
        f"• ضارب - للمضاربة\n"
        f"• ارسل - لتحويل الأموال\n"
        f"• راتب - للحصول على وظيفة\n"
        f"• عواصم - للعب لعبة العواصم\n"
        f"• الأوامر - لعرض جميع الأوامر"
    )
    context.user_data["awaiting_bank_choice"] = False


async def commands_list(update: Update, context: CallbackContext):
    commands = [
        "📜 قائمة الأوامر المتاحة:",
        "",
        "🏦 /start - إنشاء حساب بنكي جديد",
        "💰 /balance أو 'رصيدي' - عرض رصيدك الحالي",
        "📈 /invest أو 'استثمار' [المبلغ] - استثمار المبلغ لتحقيق ربح",
        "📊 /trade أو 'ضارب' [المبلغ] - المضاربة بالمبلغ (ربح أو خسارة)",
        "💸 /send أو 'ارسل' [المبلغ] [@المستخدم] - تحويل الأموال لمستخدم آخر",
        "💼 /salary أو 'راتب' - الحصول على وظيفة وراتب",
        "🌍 /capitals أو 'عواصم' - لعبة معرفة العواصم لربح المال",
        "📜 /commands أو 'الأوامر' - عرض هذه القائمة",
        "",
        "💡 ملاحظات:",
        "- عند التحويل بين نفس البنك: ضريبة 7%",
        "- عند التحويل بين بنوك مختلفة: ضريبة 15%",
        "- يمكنك الحصول على راتب كل 10 دقائق",
        "- يمكنك الاستثمار أو المضاربة كل 15 دقيقة"
    ]

    await update.message.reply_text("\n".join(commands))


async def balance(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    user_data = users[user_id]
    bank_emoji = BANKS.get(user_data.get("bank", ""), "")
    await update.message.reply_text(
        f"🆔 رقم حسابك: {user_id}\n"
        f"🏦 البنك: {bank_emoji} {user_data.get('bank', 'غير محدد')}\n"
        f"💰 الرصيد: {user_data.get('balance', 0)}$\n"
        f"💼 الوظيفة: {user_data.get('current_job', 'لا يوجد')}"
    )


def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes} دقيقة و {seconds} ثانية"


def get_timestamp(value):
    if value is None:
        return 0
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except:
            return 0
    return float(value)


async def invest(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    current_time = time.time()
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة المبلغ المراد استثماره مثال: /استثمار 100")
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا")
        return

    if amount <= 0:
        await update.message.reply_text("⚠️ المبلغ يجب أن يكون أكبر من الصفر")
        return

    if amount > users[user_id]["balance"]:
        await update.message.reply_text("⚠️ لا تملك رصيدًا كافيًا لهذا الاستثمار")
        return

    last_invest = get_timestamp(users[user_id].get("last_invest"))
    time_left = (last_invest + COOLDOWN_TIME) - current_time

    if time_left > 0:
        await update.message.reply_text(f"⏳ يجب الانتظار {format_time(time_left)} قبل الاستثمار مرة أخرى!")
        return

    profit_percent = random.uniform(0.05, 0.20)
    profit = int(amount * profit_percent)
    users[user_id]["balance"] += profit
    users[user_id]["last_invest"] = datetime.now().isoformat()
    save_data()

    await update.message.reply_text(
        f"📈 استثمرت {amount}$ وحصلت على ربح {profit}$ ({profit_percent * 100:.1f}%)\n"
        f"💰 رصيدك الجديد: {users[user_id]['balance']}$"
    )


async def trade(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    current_time = time.time()
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة المبلغ المراد مضاربته مثال: /ضارب 100")
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا")
        return

    if amount <= 0:
        await update.message.reply_text("⚠️ المبلغ يجب أن يكون أكبر من الصفر")
        return

    if amount > users[user_id]["balance"]:
        await update.message.reply_text("⚠️ لا تملك رصيدًا كافيًا لهذه المضاربة")
        return

    last_trade = get_timestamp(users[user_id].get("last_trade"))
    time_left = (last_trade + COOLDOWN_TIME) - current_time

    if time_left > 0:
        await update.message.reply_text(f"⏳ يجب الانتظار {format_time(time_left)} قبل المضاربة مرة أخرى!")
        return

    profit_percent = random.uniform(-0.50, 0.50)
    profit = int(amount * profit_percent)
    users[user_id]["balance"] += profit
    users[user_id]["last_trade"] = datetime.now().isoformat()
    save_data()

    if profit >= 0:
        await update.message.reply_text(
            f"📊 ربحت {profit}$ ({profit_percent * 100:.1f}%) من مضاربة {amount}$\n"
            f"💰 رصيدك الجديد: {users[user_id]['balance']}$"
        )
    else:
        await update.message.reply_text(
            f"📉 خسرت {-profit}$ ({abs(profit_percent) * 100:.1f}%) من مضاربة {amount}$\n"
            f"💰 رصيدك الجديد: {users[user_id]['balance']}$"
        )


async def send_money(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ يرجى كتابة المبلغ والآيدي الخاص بالمستلم مثال: /ارسل 100 123456789")
        return

    try:
        amount = int(context.args[0])
        receiver_id = str(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ المبلغ والآيدي يجب أن يكونا رقمًا صحيحًا")
        return

    if amount <= 0:
        await update.message.reply_text("⚠️ المبلغ يجب أن يكون أكبر من الصفر")
        return

    if receiver_id not in users:
        await update.message.reply_text("⚠️ لم يتم العثور على المستلم")
        return

    if user_id == receiver_id:
        await update.message.reply_text("⚠️ لا يمكن تحويل الأموال لنفسك")
        return

    # حساب الضريبة حسب البنك
    sender_bank = users[user_id].get("bank", "")
    receiver_bank = users[receiver_id].get("bank", "")

    if sender_bank == receiver_bank:
        tax_rate = SAME_BANK_TAX
        tax_message = "ضريبة تحويل (نفس البنك)"
    else:
        tax_rate = DIFFERENT_BANK_TAX
        tax_message = "ضريبة تحويل (بنوك مختلفة)"

    tax_amount = int(amount * tax_rate)
    total_cost = amount + tax_amount

    if users[user_id]["balance"] < total_cost:
        await update.message.reply_text(f"⚠️ لا تملك رصيدًا كافيًا (تحتاج {total_cost}$ بما فيها الضريبة)")
        return

    users[user_id]["balance"] -= total_cost
    users[receiver_id]["balance"] += amount
    save_data()

    await update.message.reply_text(
        f"✅ تم تحويل {amount}$ إلى العضو {receiver_id}\n"
        f"💸 تم خصم {tax_amount}$ كـ{tax_message}\n"
        f"🏦 بنك المرسل: {BANKS.get(sender_bank, '')} {sender_bank}\n"
        f"🏦 بنك المستلم: {BANKS.get(receiver_bank, '')} {receiver_bank}\n"
        f"💰 رصيدك الجديد: {users[user_id]['balance']}$"
    )


async def salary(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    current_time = time.time()
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    last_salary = get_timestamp(users[user_id].get("last_salary"))
    time_left = (last_salary + SALARY_COOLDOWN) - current_time

    if time_left > 0:
        await update.message.reply_text(f"⏳ يجب الانتظار {format_time(time_left)} قبل الحصول على راتب جديد!")
        return

    job, salary_amount = random.choice(list(JOBS.items()))
    users[user_id]["current_job"] = job
    users[user_id]["balance"] += salary_amount
    users[user_id]["last_salary"] = datetime.now().isoformat()
    save_data()

    await update.message.reply_text(
        f"🎉 لقد حصلت على وظيفة جديدة!\n"
        f"💼 الوظيفة: {job}\n"
        f"💰 الراتب: {salary_amount}$\n"
        f"💵 رصيدك الجديد: {users[user_id]['balance']}$\n"
        f"⏱️ يمكنك الحصول على راتب جديد بعد 10 دقائق"
    )


async def capitals_game(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not is_group_chat(update):
        await update.message.reply_text("🚫 هذا البوت يعمل فقط في المجموعات!")
        return

    if user_id not in users:
        await update.message.reply_text("⚠️ ليس لديك حساب بنكي! اكتب /start لإنشاء حساب")
        return

    if "capitals_answered" not in users[user_id]:
        users[user_id]["capitals_answered"] = []
        save_data()

    unanswered = [country for country in capitals if country not in users[user_id]["capitals_answered"]]

    if not unanswered:
        users[user_id]["capitals_answered"] = []
        unanswered = list(capitals.keys())
        save_data()

    country = random.choice(unanswered)
    context.user_data["current_country"] = country
    await update.message.reply_text(f"ما هي عاصمة {country}؟")


async def check_capital_answer(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_answer = update.message.text.strip()

    if "current_country" not in context.user_data:
        return

    country = context.user_data["current_country"]
    correct_answer = capitals.get(country, "")

    if user_answer.lower() == correct_answer.lower():
        users[user_id]["balance"] += 200
        if "capitals_answered" not in users[user_id]:
            users[user_id]["capitals_answered"] = []
        users[user_id]["capitals_answered"].append(country)
        save_data()
        await update.message.reply_text(f"✅ إجابة صحيحة! لقد ربحت 200$\n💰 رصيدك الآن: {users[user_id]['balance']}$")
        del context.user_data["current_country"]
    else:
        await update.message.reply_text(f"❌ إجابة خاطئة! العاصمة الصحيحة هي {correct_answer}")


async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == 'admin_back':
        await show_admin_panel(update, context)
    elif data == 'groups_list':
        await admin_groups_list(update, context)
    elif data == 'send_money_group':
        await admin_groups_list(update, context)
        context.user_data['admin_action'] = 'send_money_group'
    elif data.startswith('group_'):
        await admin_group_detail(update, context)
    elif data.startswith('member_'):
        await admin_member_detail(update, context)
    elif data.startswith('send_'):
        await admin_send_money(update, context)
    elif data.startswith('send_all_'):
        await admin_send_money(update, context)


# معالجة الرسائل النصية
async def message_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # إذا كان الرسالة من المشرف في المحادثة الخاصة
    if update.effective_user.id == ADMIN_ID and not is_group_chat(update):
        await handle_admin_message(update, context)
        return

    # التحقق من اختيار البنك
    if context.user_data.get("awaiting_bank_choice", False) and user_id not in users:
        await handle_bank_choice(update, context)
        return

    parts = text.split()
    command = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    commands = {
        "ابدأ": start,
        "رصيدي": balance,
        "استثمر": invest,
        "ضارب": trade,
        "ارسل": send_money,
        "راتب": salary,
        "عواصم": capitals_game,
        "الاوامر": commands_list
    }

    if command in commands:
        context.args = args
        await commands[command](update, context)
    elif "current_country" in context.user_data:
        await check_capital_answer(update, context)


# تكوين البوت
TOKEN = "7491328318:AAHWTiXXhgHGn4kZhxSmS300iWtzwG5sEJI"
app = Application.builder().token(TOKEN).build()

# إضافة معالجات الأوامر
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("invest", invest))
app.add_handler(CommandHandler("trade", trade))
app.add_handler(CommandHandler("send", send_money))
app.add_handler(CommandHandler("salary", salary))
app.add_handler(CommandHandler("capitals", capitals_game))
app.add_handler(CommandHandler("commands", commands_list))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
app.add_handler(CallbackQueryHandler(button_callback))

# تشغيل البوت
print("✅ البوت يعمل الآن...")
app.run_polling()
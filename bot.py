from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import datetime
import json
import os
import pandas as pd

# ЗАМЕНИТЕ НА ВАШ ТОКЕН ОТ @BotFather!
TOKEN = "8242070126:AAFBa_2bkZucqwk-nAhkzX3FNMOpsWeSXZ0"

# Файлы для сохранения данных
BOOKINGS_FILE = "bookings.json"
OCCUPIED_SLOTS_FILE = "occupied_slots.json"
RULES_FILE = "rules.txt"  # Файл с правилами

# Данные расписания спортивного зала
SCHEDULE_DATA = {
    'День недели': ['Понедельник', 'Понедельник', 'Понедельник',
                    'Вторник', 'Вторник', 'Вторник', 'Вторник',
                    'Среда', 'Среда', 'Среда',
                    'Четверг', 'Четверг', 'Четверг', 'Четверг',
                    'Пятница', 'Пятница', 'Пятница', 'Пятница',
                    'Суббота', 'Суббота', 'Суббота', 'Суббота', 'Суббота', 'Суббота', 'Суббота', 'Суббота',
                    'Воскресенье', 'Воскресенье', 'Воскресенье', 'Воскресенье', 'Воскресенье', 'Воскресенье',
                    'Воскресенье', 'Воскресенье'],
    'Начало': ['07:00:00', '18:30:00', '20:00:00',
               '07:30:00', '18:15:00', '19:15:00', '20:45:00',
               '07:00:00', '18:30:00', '20:00:00',
               '07:30:00', '18:15:00', '19:15:00', '20:45:00',
               '07:00:00', '17:00:00', '18:30:00', '20:00:00',
               '08:00:00', '10:00:00', '12:00:00', '14:00:00', '16:00:00', '17:30:00', '19:00:00', '21:00:00',
               '08:00:00', '10:00:00', '12:00:00', '14:00:00', '16:00:00', '18:00:00', '19:30:00', '21:30:00'],
    'Окончание': ['08:30:00', '20:00:00', '21:30:00',
                  '08:30:00', '19:15:00', '20:45:00', '22:45:00',
                  '08:30:00', '20:00:00', '21:30:00',
                  '08:30:00', '19:15:00', '20:45:00', '22:15:00',
                  '08:30:00', '18:30:00', '20:00:00', '22:00:00',
                  '10:00:00', '12:00:00', '14:00:00', '16:00:00', '17:30:00', '19:00:00', '21:00:00', '22:30:00',
                  '10:00:00', '12:00:00', '14:00:00', '16:00:00', '18:00:00', '19:30:00', '21:30:00', '22:30:00'],
    'Вид спорта': ['Теннис (большой)', 'Волейбол (жен)', 'Мини-футбол',
                   'Йога', 'Фитнес', 'Волейбол (муж)', 'Теннис (большой)',
                   'Теннис (большой)', 'Баскетбол', 'Теннис (большой)',
                   'Йога', 'Фитнес', 'Мини-футбол', 'Волейбол (муж)',
                   'Теннис (большой)', 'Баскетбол', 'Волейбол (жен)', 'Теннис (большой)',
                   'Теннис (большой)', 'Бадминтон', 'Баскетбол', 'По резерву', 'По резерву', 'По резерву',
                   'Теннис (большой)', 'По резерву',
                   'Баскетбол', 'Теннис (большой)', 'По резерву', 'По резерву', 'Баскетбол', 'Мини-футбол',
                   'По резерву', 'По резерву'],
    'Ответственное лицо': ['Быбин Петр / Щуклин Алексей', 'Сазонова Анна/Чернявских Мария',
                           'Кочетков Павел/Сазонов Николай',
                           'Подшивалов Андрей/Горобец Вячеслав', 'Яковлева Ксения',
                           'Перевалов Леонид/Листойкин Дмитрий', 'Быбин Петр/Щуклин Алексей',
                           'Быбин Петр/Щуклин Алексей', 'Квартников Дмитрий/Туляков Ильгиз',
                           'Быбин Петр/Щуклин Алексей',
                           'Подшивалов Андрей/Горобец Вячеслав', 'Яковлева Ксения', 'Кочетков Павел/Сазонов Николай',
                           'Перевалов Леонид/Листойкин Дмитрий',
                           'Быбин Петр/Щуклин Алексей', 'Квартников Дмитрий/Туляков Ильгиз',
                           'Сазонова Анна/Чернявских Мария', 'Быбин Петр/Щуклин Алексей',
                           'Быбин Петр/Щуклин Алексей', 'Гуляев Денис/Казанцев Глеб',
                           'Квартников Дмитрий/Туляков Ильгиз', '', '', '', 'Быбин Петр/Щуклин Алексей', '',
                           'Квартников Дмитрий/Туляков Ильгиз', 'Быбин Петр/Щуклин Алексей', '', '',
                           'Квартников Дмитрий/Туляков Ильгиз', 'Кочетков Павел/Сазонов Николай', '', ''],
    'Имя пользователя': ['@PetrBybin | @Alexey_Shchuklin', '@username | @username', '@username | @username',
                         '@AndreyP_Yoga | @slava_gorobets', '@username | @username', '@username | @username',
                         '@PetrBybin | @Alexey_Shchuklin',
                         '@PetrBybin | @Alexey_Shchuklin', '@username | @username', '@PetrBybin | @Alexey_Shchuklin',
                         '@AndreyP_Yoga | @slava_gorobets', '@username | @username', '@username | @username',
                         '@username | @Dmitry_Listoykin',
                         '@PetrBybin | @Alexey_Shchuklin', '@username | @username', '@username | @username',
                         '@PetrBybin | @Alexey_Shchuklin',
                         '@PetrBybin | @Alexey_Shchuklin', '@username | @username', '@username | @username', '', '', '',
                         '@PetrBybin | @Alexey_Shchuklin', '',
                         '@username | @username', '@PetrBybin | @Alexey_Shchuklin', '', '', '@username | @username',
                         '@username | @username', '', '']
}


# Загрузка правил из файла
def load_rules():
    """Загружает правила из файла rules.txt"""
    try:
        if os.path.exists(RULES_FILE):
            with open(RULES_FILE, 'r', encoding='utf-8') as f:
                rules_text = f.read().strip()
                if rules_text:
                    return rules_text
                else:
                    print("Файл rules.txt пуст")
        else:
            print(f"Файл {RULES_FILE} не найден")
    except Exception as e:
        print(f"Ошибка загрузки правил: {e}")

    # Возвращаем правила по умолчанию, если файл не найден или пуст
    return """📋 Правила использования зала НТЦ:

• Бронь за 2 часа до игры
• Отмена за 1 час до игры  
• Зал бесплатен для участников клуба
• Спортивная форма обязательна
• Соблюдайте расписание
• Бережно относитесь к оборудованию
• Уважайте других участников"""


# Загрузка расписания
def load_schedule():
    df = pd.DataFrame(SCHEDULE_DATA)
    # Явно указываем формат времени для избежания предупреждений
    df['Начало'] = pd.to_datetime(df['Начало'], format='%H:%M:%S').dt.time
    df['Окончание'] = pd.to_datetime(df['Окончание'], format='%H:%M:%S').dt.time
    return df


# Получение временных слотов для конкретного дня
def get_time_slots_for_day(day_ru):
    schedule_df = load_schedule()
    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]

    time_slots = []
    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        time_slots.append(f"{start_str}-{end_str}")

    return time_slots


# Получение информации о слоте
def get_slot_info(day_ru, time_slot):
    """Возвращает информацию о слоте"""
    schedule_df = load_schedule()
    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]

    print(f"DEBUG get_slot_info: Looking for {day_ru} {time_slot}")
    print(f"DEBUG get_slot_info: Available slots in {day_ru}:")

    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        current_slot = f"{start_str}-{end_str}"
        sport_type = slot['Вид спорта']
        print(f"DEBUG get_slot_info: - {current_slot}: {sport_type}")

        if current_slot == time_slot:
            result = {
                'sport_type': slot['Вид спорта'],
                'responsible': slot['Ответственное лицо'],
                'usernames': slot['Имя пользователя']
            }
            print(f"DEBUG get_slot_info: Found slot: {result}")
            return result

    print(f"DEBUG get_slot_info: Slot not found for {day_ru} {time_slot}")
    return None


# Создание кнопок для ответственных лиц
def create_responsible_buttons(responsible_text, usernames_text):
    buttons = []

    if not responsible_text or not usernames_text:
        return buttons

    # Разделяем ответственных лиц
    responsible_persons = [p.strip() for p in responsible_text.split('/')]
    username_list = [u.strip() for u in usernames_text.split('|')]

    for i, person in enumerate(responsible_persons):
        if i < len(username_list):
            username = username_list[i].replace('@', '').strip()
            if username and username != 'username':
                buttons.append([
                    InlineKeyboardButton(
                        f"👤 {person}",
                        url=f"https://t.me/{username}"
                    )
                ])

    return buttons


# Русские названия дней недели
RUSSIAN_DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']


# Загрузка данных при запуске
def load_data():
    global bookings, occupied_slots
    try:
        if os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, 'r', encoding='utf-8') as f:
                bookings = json.load(f)
                # Конвертируем ключи из str в int (user_id)
                bookings = {int(k): v for k, v in bookings.items()}
        else:
            bookings = {}
    except:
        bookings = {}

    try:
        if os.path.exists(OCCUPIED_SLOTS_FILE):
            with open(OCCUPIED_SLOTS_FILE, 'r', encoding='utf-8') as f:
                occupied_slots = json.load(f)
        else:
            occupied_slots = {}
    except:
        occupied_slots = {}


# Сохранение данных
def save_data():
    try:
        with open(BOOKINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookings, f, ensure_ascii=False, indent=2)
        with open(OCCUPIED_SLOTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(occupied_slots, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")


# Загружаем данные при запуске
load_data()

# Название зала
HALL_NAME = "🏸 Спортивный зал НТЦ"


# Функции для проверки доступности слотов
def is_slot_available(date_str, time_slot):
    """Проверяет, свободно ли время"""
    slot_key = f"{date_str}_{time_slot}"
    return slot_key not in occupied_slots


def get_booking_info(date_str, time_slot):
    """Возвращает информацию о брони"""
    slot_key = f"{date_str}_{time_slot}"
    if slot_key in occupied_slots:
        user_id = occupied_slots[slot_key]['user_id']
        if user_id in bookings:
            # Ищем бронь по дате и времени
            for booking in bookings[user_id]:
                if booking['date'] == date_str and booking['time'] == time_slot:
                    return booking
    return None


def reserve_slot(date_str, time_slot, user_id):
    """Резервирует время"""
    slot_key = f"{date_str}_{time_slot}"
    occupied_slots[slot_key] = {
        'user_id': user_id,
        'reserved_at': datetime.datetime.now().isoformat()
    }
    save_data()


def free_slot(date_str, time_slot):
    """Освобождает время"""
    slot_key = f"{date_str}_{time_slot}"
    if slot_key in occupied_slots:
        del occupied_slots[slot_key]
        save_data()


def add_booking(user_id, booking_data):
    """Добавляет бронь в список броней пользователя"""
    if user_id not in bookings:
        bookings[user_id] = []
    bookings[user_id].append(booking_data)
    save_data()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏸 💪 Забронировать зал", callback_data="select_date")],
        [InlineKeyboardButton("📅 Расписание", callback_data="schedule")],
        [InlineKeyboardButton("📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton("ℹ️ Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏸 💪 Добро пожаловать в спортивный клуб НТЦ!\n\n"
        "Зал доступен для бронирования участникам клуба.\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def start_from_query(query):
    """Главное меню из callback query"""
    keyboard = [
        [InlineKeyboardButton("🏸 Забронировать зал", callback_data="select_date")],
        [InlineKeyboardButton("📅 Расписание", callback_data="schedule")],
        [InlineKeyboardButton("📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton("ℹ️ Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🏸 Добро пожаловать в спортивный клуб НТЦ!\n\n"
        "Зал доступен для бронирования участникам клуба.\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def show_dates(query):
    """Показывает доступные даты для бронирования"""
    keyboard = []
    today = datetime.datetime.now()

    # Показываем 7 дней вперед
    for i in range(7):
        date = today + datetime.timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        day_name_ru = RUSSIAN_DAYS[date.weekday()]

        keyboard.append([
            InlineKeyboardButton(
                f"{date_str} ({day_name_ru})",
                callback_data=f"date_{date_str}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📅 Выберите дату для бронирования:",
        reply_markup=reply_markup
    )


async def show_times(query, date_str):
    """Показывает доступное время для выбранной даты"""
    # Получаем русское название дня недели для выбранной даты
    date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
    day_ru = RUSSIAN_DAYS[date_obj.weekday()]

    # Получаем временные слоты для этого дня из расписания
    time_slots = get_time_slots_for_day(day_ru)

    if not time_slots:
        await query.edit_message_text(
            f"❌ На {date_str} ({day_ru}) зал не работает.\nВыберите другую дату.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад к выбору даты", callback_data="select_date")]
            ])
        )
        return

    # Получаем информацию о слотах для отображения статуса
    schedule_df = load_schedule()
    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]

    keyboard = []

    # Создаем кнопки времени - ВСЕ слоты можно бронировать
    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        time_slot = f"{start_str}-{end_str}"
        sport_type = slot['Вид спорта']

        # Для всех слотов показываем возможность бронирования
        if is_slot_available(date_str, time_slot):
            if sport_type == 'По резерву':
                keyboard.append([InlineKeyboardButton(
                    f"🟢 {time_slot} - Свободно",
                    callback_data=f"time_{date_str}_{time_slot}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    f"🟢 {time_slot} - {sport_type} (рекомендуется)",
                    callback_data=f"time_{date_str}_{time_slot}"
                )])
        else:
            # Занятые слоты
            keyboard.append([InlineKeyboardButton(
                f"🔴 {time_slot} - Занято",
                callback_data=f"details_{date_str}_{time_slot}"
            )])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="select_date")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🕐 Выберите время на {date_str} ({day_ru}):\n\n"
        f"🟢 - свободно для брони\n"
        f"🔴 - уже забронировано\n\n"
        f"<i>Вид спорта указан как рекомендуемый, но вы можете выбрать любой</i>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def select_sport_type(query, user_id, user_name, date_str, time_slot):
    """Выбор вида спорта с учетом рекомендуемого из расписания"""
    # Получаем рекомендуемый вид спорта из расписания
    date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
    day_ru = RUSSIAN_DAYS[date_obj.weekday()]
    slot_info = get_slot_info(day_ru, time_slot)

    recommended_sport = slot_info['sport_type'] if slot_info and slot_info['sport_type'] != 'По резерву' else None

    sport_keyboard = []

    # Если есть рекомендуемый вид спорта, показываем его первым
    if recommended_sport:
        sport_keyboard.append([
            InlineKeyboardButton(
                f"🎯 {recommended_sport} (рекомендуется)",
                callback_data=f"sport_{date_str}_{time_slot}_{recommended_sport}"
            )
        ])

    # Остальные виды спорта
    other_sports = [
        "Бадминтон", "Настольный теннис", "Волейбол",
        "Мини-футбол", "Йога", "Фитнес", "Теннис (большой)", "Баскетбол"
    ]

    # Убираем рекомендуемый вид спорта из общего списка, если он есть
    if recommended_sport and recommended_sport in other_sports:
        other_sports.remove(recommended_sport)

    # Добавляем остальные виды спорта по 2 в ряд
    for i in range(0, len(other_sports), 2):
        row = []
        if i < len(other_sports):
            sport1 = other_sports[i]
            emoji1 = get_sport_emoji(sport1)
            row.append(InlineKeyboardButton(
                f"{emoji1} {sport1}",
                callback_data=f"sport_{date_str}_{time_slot}_{sport1}"
            ))
        if i + 1 < len(other_sports):
            sport2 = other_sports[i + 1]
            emoji2 = get_sport_emoji(sport2)
            row.append(InlineKeyboardButton(
                f"{emoji2} {sport2}",
                callback_data=f"sport_{date_str}_{time_slot}_{sport2}"
            ))
        if row:
            sport_keyboard.append(row)

    sport_keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"date_{date_str}")])
    reply_markup = InlineKeyboardMarkup(sport_keyboard)

    recommendation_text = f"\n\n🎯 <b>Рекомендуется:</b> {recommended_sport}" if recommended_sport else ""

    await query.edit_message_text(
        f"🏸 Выберите вид спорта для {date_str} {time_slot}:{recommendation_text}",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


def get_sport_emoji(sport_type):
    """Возвращает эмодзи для вида спорта"""
    emoji_map = {
        "Бадминтон": "🎾",
        "Настольный теннис": "🏓",
        "Волейбол": "🏐",
        "Мини-футбол": "⚽",
        "Йога": "🧘",
        "Фитнес": "💪",
        "Теннис (большой)": "🎾",
        "Баскетбол": "🏀"
    }
    return emoji_map.get(sport_type, "🏸")


async def confirm_booking(query, user_id, user_name, date_str, time_slot, sport_type):
    """Подтверждение бронирования"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить бронь", callback_data=f"confirm_{date_str}_{time_slot}_{sport_type}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"date_{date_str}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📋 Подтвердите бронь:\n\n"
        f"• Зал: {HALL_NAME}\n"
        f"• Дата: {date_str}\n"
        f"• Время: {time_slot}\n"
        f"• Вид спорта: {sport_type}\n"
        f"• Имя: {user_name}\n"
        f"Всё верно?",
        reply_markup=reply_markup
    )


async def finalize_booking(query, user_id, user_name, date_str, time_slot, sport_type):
    """Завершение бронирования"""
    reserve_slot(date_str, time_slot, user_id)

    booking_id = f"B{int(datetime.datetime.now().timestamp())}"

    # Получаем username пользователя
    username = query.from_user.username

    booking_data = {
        'id': booking_id,
        'hall': HALL_NAME,
        'time': time_slot,
        'date': date_str,
        'sport_type': sport_type,
        'price': "Бесплатно",
        'name': user_name,
        'username': username  # Сохраняем username
    }

    add_booking(user_id, booking_data)

    await query.edit_message_text(
        f"✅ Бронь подтверждена!\n\n"
        f"📋 Детали:\n"
        f"• ID: {booking_id}\n"
        f"• Зал: {HALL_NAME}\n"
        f"• Дата: {date_str}\n"
        f"• Время: {time_slot}\n"
        f"• Вид спорта: {sport_type}\n"
        f"• Стоимость: Бесплатно\n\n"
        f"Ждем вас в клубе! 🏸"
    )


async def show_contact_details(query, booking_info, date_str, time_slot):
    """Показывает детальную информацию с кликабельными ссылками"""

    contact_text = (
        f"🔍 Информация о брони:\n\n"
        f"⏰ <b>Время занято:</b>\n"
        f"📅 <b>Дата:</b> {date_str}\n"
        f"🕐 <b>Время:</b> {time_slot}\n"
        f"🎯 <b>Вид спорта:</b> {booking_info['sport_type']}\n"
        f"👤 <b>Имя:</b> {booking_info['name']}\n"
        f"💰 <b>Стоимость:</b> {booking_info['price']}\n\n"
    )

    keyboard = []

    # Добавляем кнопку для связи если есть username
    if booking_info.get('username'):
        username = booking_info['username']
        contact_text += f"💬 <b>Telegram:</b> @{username}\n\n"
        contact_text += "👇 Нажмите кнопку ниже для связи:"

        # Создаем кнопку с ссылкой на пользователя
        keyboard.append([
            InlineKeyboardButton(
                f"✉️ Написать @{username}",
                url=f"https://t.me/{username}"
            )
        ])
    else:
        contact_text += "❌ <b>Username не указан</b>\n"
        contact_text += "📞 <b>Свяжитесь через администратора</b>"

    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton("🔙 Назад к выбору времени", callback_data=f"date_{date_str}")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        contact_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def cancel_specific_booking(query, user_id, booking_id):
    """Отменяет конкретную бронь"""
    if user_id in bookings:
        user_bookings = bookings[user_id]
        # Ищем бронь по ID
        for booking in user_bookings[:]:  # Используем копию для безопасного удаления
            if booking['id'] == booking_id:
                # Освобождаем время
                free_slot(booking['date'], booking['time'])
                # Удаляем бронь из списка
                user_bookings.remove(booking)
                # Если броней не осталось, удаляем пользователя из словаря
                if not user_bookings:
                    del bookings[user_id]
                save_data()

                await query.edit_message_text(
                    f"✅ Бронь отменена!\n"
                    f"🗓️ {booking['date']} {booking['time']}\n"
                    f"🎯 {booking['sport_type']}\n"
                    f"Время освобождено для других."
                )
                return

        await query.edit_message_text("❌ Бронь не найдена")
    else:
        await query.edit_message_text("❌ У вас нет активных броней")


async def show_user_bookings(query, user_id):
    """Показывает все брони пользователя"""
    if user_id in bookings and bookings[user_id]:
        user_bookings = bookings[user_id]

        # Сортируем брони по дате и времени
        sorted_bookings = sorted(user_bookings, key=lambda x: (
            datetime.datetime.strptime(x['date'], "%d.%m.%Y"),
            x['time']
        ))

        bookings_text = "📋 Ваши активные брони:\n\n"

        keyboard = []
        for booking in sorted_bookings:
            bookings_text += (
                f"• 🆔 ID: {booking['id']}\n"
                f"  📅 Дата: {booking['date']}\n"
                f"  🕐 Время: {booking['time']}\n"
                f"  🎯 Вид спорта: {booking['sport_type']}\n"
                f"  💰 Стоимость: {booking['price']}\n"
                f"  ────────────────────\n"
            )
            # Добавляем кнопку для отмены каждой брони
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Отменить {booking['date']} {booking['time']}",
                    callback_data=f"cancel_{booking['id']}"
                )
            ])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(bookings_text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(
            "❌ У вас нет активных броней\n\n"
            "Нажмите '🏸 Забронировать зал' чтобы создать первую бронь!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏸 Забронировать зал", callback_data="select_date")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])
        )


async def show_weekly_schedule(query):
    """Показывает расписание на всю неделю в виде красивой таблицы"""
    schedule_df = load_schedule()

    schedule_text = "📅 <b>РАСПИСАНИЕ СПОРТИВНОГО ЗАЛА НТЦ</b>\n\n"

    for day in RUSSIAN_DAYS:
        day_schedule = schedule_df[schedule_df['День недели'] == day]
        if not day_schedule.empty:
            schedule_text += f"<b>┌─── {day.upper()} ───</b>\n"

            for _, slot in day_schedule.iterrows():
                start_str = slot['Начало'].strftime('%H:%M')
                end_str = slot['Окончание'].strftime('%H:%M')
                sport_type = slot['Вид спорта']

                # Форматируем строку
                time_display = f"{start_str}-{end_str}"
                sport_display = sport_type if sport_type else "Свободно"

                if sport_type == 'По резерву':
                    schedule_text += f"│ 🟢 <code>{time_display:^11}</code> │ Свободно для брони\n"
                else:
                    schedule_text += f"│ 🔵 <code>{time_display:^11}</code> │ {sport_display}\n"

            schedule_text += "└─────────────────────────────\n\n"

    schedule_text += "\n<code>🟢</code> - свободно для брони\n<code>🔵</code> - регулярное занятие\n\nНажмите на кнопку дня для деталей👇"

    # Кнопки для каждого дня
    keyboard = []
    for i in range(0, 7, 2):
        row = []
        if i < 7:
            row.append(InlineKeyboardButton(f"📅 {RUSSIAN_DAYS[i]}", callback_data=f"day_{RUSSIAN_DAYS[i]}"))
        if i + 1 < 7:
            row.append(InlineKeyboardButton(f"📅 {RUSSIAN_DAYS[i + 1]}", callback_data=f"day_{RUSSIAN_DAYS[i + 1]}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        schedule_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_day_schedule(query, day_ru):
    """Показывает детальное расписание на конкретный день"""
    await query.answer()  # Подтверждаем нажатие кнопки

    schedule_df = load_schedule()
    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]

    if day_schedule.empty:
        await query.edit_message_text(
            f"❌ На {day_ru} зал не работает.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад к расписанию", callback_data="schedule")]
            ])
        )
        return

    schedule_text = f"📅 <b>РАСПИСАНИЕ НА {day_ru.upper()}</b>\n\n"

    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        sport_type = slot['Вид спорта']
        responsible = slot['Ответственное лицо']

        time_display = f"{start_str}-{end_str}"

        if sport_type == 'По резерву':
            schedule_text += f"🟢 <b>{time_display}</b> - Свободно для брони\n"
        else:
            schedule_text += f"🔵 <b>{time_display}</b> - {sport_type}\n"
            if responsible:
                schedule_text += f"   👥 {responsible}\n"
        schedule_text += "\n"

    # Кнопки для каждого временного слота
    keyboard = []
    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        time_slot = f"{start_str}-{end_str}"
        sport_type = slot['Вид спорта']

        if sport_type == 'По резерву':
            button_text = f"🟢 {time_slot} - Свободно"
        else:
            button_text = f"🔵 {time_slot} - {sport_type}"

        # Упрощаем callback_data - убираем пробелы и скобки
        day_simple = day_ru[:3]  # Берем первые 3 буквы дня
        time_simple = time_slot.replace(':', '').replace('-', '')  # Убираем : и -
        sport_simple = sport_type.split(' ')[0]  # Берем первое слово из вида спорта

        callback_data = f"slot_{day_simple}_{time_simple}"
        print(f"DEBUG: Creating button: {button_text} -> {callback_data}")

        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад к расписанию", callback_data="schedule")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        schedule_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_slot_details(query, date_str, time_slot, slot_info):
    """Показывает детальную информацию о регулярном занятии"""
    date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
    day_ru = RUSSIAN_DAYS[date_obj.weekday()]

    print(f"DEBUG: show_slot_details: day={day_ru}, time={time_slot}, info={slot_info}")

    # Если слот не найден, это означает ошибку в данных
    if not slot_info:
        await query.answer("❌ Ошибка: информация о времени не найдена", show_alert=True)
        return

    # Проверяем, есть ли информация о регулярном занятии
    if slot_info['sport_type'] != 'По резерву':
        detail_text = (
            f"🔵 <b>Регулярное занятие</b>\n\n"
            f"📅 <b>День:</b> {day_ru}\n"
            f"🕐 <b>Время:</b> {time_slot}\n"
            f"🎯 <b>Вид спорта:</b> {slot_info['sport_type']}\n"
            f"👥 <b>Ответственные:</b> {slot_info['responsible']}\n\n"
            f"<i>Это регулярное занятие. Для участия свяжитесь с ответственными:</i>"
        )

        # Создаем кнопки для ответственных лиц
        keyboard = create_responsible_buttons(slot_info['responsible'], slot_info['usernames'])
    else:
        detail_text = (
            f"🟢 <b>Свободное время</b>\n\n"
            f"📅 <b>День:</b> {day_ru}\n"
            f"🕐 <b>Время:</b> {time_slot}\n\n"
            f"<i>Это время свободно для бронирования!</i>"
        )
        keyboard = []

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"day_{day_ru}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        detail_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_rules(query):
    """Показывает правила из файла rules.txt"""
    # Загружаем правила каждый раз при нажатии на кнопку
    rules_text = load_rules()

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        rules_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name or "Пользователь"

    print(f"DEBUG: Button pressed: {query.data}")

    try:
        # Обработка всплывающих окон (должна быть ДО await query.answer())
        if query.data.startswith("info_"):
            data_parts = query.data.replace("info_", "").split("_")
            date_str = data_parts[0]
            time_slot = data_parts[1]

            booking_info = get_booking_info(date_str, time_slot)
            if booking_info:
                # Показываем краткую информацию во всплывающем окне
                await query.answer(
                    f"⏰ {date_str} {time_slot}\n"
                    f"👤 {booking_info['name']}\n"
                    f"🎯 {booking_info['sport_type']}\n"
                    f"Нажмите 'Подробнее' для связи",
                    show_alert=True
                )
            else:
                await query.answer("❌ Информация о брони не найдена", show_alert=True)
            return

        elif query.data.startswith("slot_"):
            # Показываем информацию о регулярном занятии (упрощенный формат)
            data_parts = query.data.replace("slot_", "").split("_")
            day_short = data_parts[0]
            time_simple = data_parts[1]

            # Восстанавливаем полное название дня
            day_map = {
                'Пон': 'Понедельник',
                'Вто': 'Вторник',
                'Сре': 'Среда',
                'Чет': 'Четверг',
                'Пят': 'Пятница',
                'Суб': 'Суббота',
                'Вос': 'Воскресенье'
            }
            day_ru = day_map.get(day_short, day_short)

            # Восстанавливаем нормальный формат времени
            if len(time_simple) == 8:  # 08001000
                time_slot = f"{time_simple[:2]}:{time_simple[2:4]}-{time_simple[4:6]}:{time_simple[6:8]}"
            else:
                time_slot = time_simple

            print(f"DEBUG: Processing slot: day={day_ru}, time={time_slot}")

            slot_info = get_slot_info(day_ru, time_slot)
            print(f"DEBUG: Slot info: {slot_info}")

            if not slot_info:
                await query.answer("❌ Информация о времени не найдена", show_alert=True)
                return

            # Создаем фиктивную дату для отображения
            today = datetime.datetime.now()
            days_ahead = (RUSSIAN_DAYS.index(day_ru) - today.weekday()) % 7
            target_date = today + datetime.timedelta(days=days_ahead)
            date_str = target_date.strftime("%d.%m.%Y")

            await show_slot_details(query, date_str, time_slot, slot_info)
            return

        elif query.data.startswith("details_"):
            # Показываем детальную информацию с кликабельными ссылками
            data_parts = query.data.replace("details_", "").split("_")
            date_str = data_parts[0]
            time_slot = data_parts[1]

            booking_info = get_booking_info(date_str, time_slot)
            if booking_info:
                await show_contact_details(query, booking_info, date_str, time_slot)
            return

        elif query.data.startswith("cancel_"):
            # Обработка отмены конкретной брони
            booking_id = query.data.replace("cancel_", "")
            await cancel_specific_booking(query, user_id, booking_id)
            return

        elif query.data.startswith("day_"):
            # Обработка кнопок дней недели
            day_ru = query.data.replace("day_", "")
            await show_day_schedule(query, day_ru)
            return

        # Для остальных кнопок
        await query.answer()

        if query.data == "select_date":
            await show_dates(query)

        elif query.data == "schedule":
            await show_weekly_schedule(query)

        elif query.data == "back_to_main":
            await start_from_query(query)

        elif query.data.startswith("date_"):
            date_str = query.data.replace("date_", "")
            await show_times(query, date_str)

        elif query.data.startswith("time_"):
            data_parts = query.data.replace("time_", "").split("_")
            date_str = data_parts[0]
            time_slot = data_parts[1]

            if is_slot_available(date_str, time_slot):
                await select_sport_type(query, user_id, user_name, date_str, time_slot)
            else:
                await query.edit_message_text(
                    "❌ Это время уже занято!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад к выбору времени", callback_data=f"date_{date_str}")]
                    ])
                )

        elif query.data.startswith("sport_"):
            data_parts = query.data.replace("sport_", "").split("_")
            date_str = data_parts[0]
            time_slot = data_parts[1]
            sport_type = data_parts[2]

            if is_slot_available(date_str, time_slot):
                await confirm_booking(query, user_id, user_name, date_str, time_slot, sport_type)
            else:
                await query.edit_message_text(
                    "❌ Это время только что заняли!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Выбрать другое время", callback_data=f"date_{date_str}")]
                    ])
                )

        elif query.data.startswith("confirm_"):
            data_parts = query.data.replace("confirm_", "").split("_")
            date_str = data_parts[0]
            time_slot = data_parts[1]
            sport_type = data_parts[2]

            if is_slot_available(date_str, time_slot):
                await finalize_booking(query, user_id, user_name, date_str, time_slot, sport_type)
            else:
                await query.edit_message_text(
                    "❌ Это время только что заняли!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Выбрать другое время", callback_data=f"date_{date_str}")]
                    ])
                )

        elif query.data == "my_bookings":
            await show_user_bookings(query, user_id)

        elif query.data == "rules":
            await show_rules(query)

        else:
            print(f"DEBUG: Unknown button: {query.data}")
            await query.answer("❌ Неизвестная команда")

    except Exception as e:
        print(f"ERROR in handle_button: {e}")
        # Пытаемся ответить на запрос, если он еще валиден
        try:
            await query.answer("❌ Произошла ошибка, попробуйте еще раз")
        except:
            pass  # Игнорируем ошибку, если запрос уже невалиден


def main():
    print("🔄 Запуск бота...")
    print(f"📊 Загружено пользователей с бронями: {len(bookings)}")

    total_bookings = sum(len(user_bookings) for user_bookings in bookings.values())
    print(f"📊 Всего броней: {total_bookings}")
    print(f"📊 Занятых слотов: {len(occupied_slots)}")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    print("✅ Бот запущен! Для остановки нажмите Ctrl+C")
    application.run_polling()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ошибки"""
    print(f"Exception while handling an update: {context.error}")


if __name__ == "__main__":
    main()
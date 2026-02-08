from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import datetime
import json
import os
import pandas as pd
from flask import Flask, request, jsonify
import threading

# Создаем Flask приложение
app = Flask(__name__)
# Глобальная переменная для бота
application = None
# Токен бота
TOKEN = "8266158494:AAF-VfMR9nJWC5UIAfkZCnCurfrQmoJTXsY"

# Файлы для сохранения данных
BOOKINGS_FILE = "bookings.json"
OCCUPIED_SLOTS_FILE = "occupied_slots.json"
SCHEDULE_FILE = "inDATA.xlsx"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Загрузка правил из файла Excel
def load_rules():
    """Загружает правила из вкладки rules в Excel файле"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if os.path.exists(schedule_path):
            df_rules = pd.read_excel(schedule_path, sheet_name='rules')

            # Объединяем все строки в один текст с разделителями
            rules_text = "📋 <b>ПРАВИЛА ИСПОЛЬЗОВАНИЯ СПОРТИВНОГО ЗАЛА НТЦ</b>\n\n"

            rules_list = []
            for _, row in df_rules.iterrows():
                rule_line = str(row.iloc[0]).strip()
                if rule_line and rule_line != 'nan' and rule_line != 'None':
                    rules_list.append(rule_line)

            # Форматируем правила с разделителями
            for i, rule in enumerate(rules_list, 1):
                rules_text += f"▪️ {rule}\n"
                if i < len(rules_list):  # Не добавляем линию после последнего пункта
                    rules_text += "─────────────────\n"

            if rules_text.strip():
                # Добавляем информацию о разработчике
                rules_text += f"\n\n🤖 <b>Разработчик:</b> @RomanenkoIE"
                return rules_text.strip()

    except Exception as e:
        print(f"Ошибка загрузки правил: {e}")

    return "❌ Правила временно недоступны"


# Загрузка расписания из Excel
def load_schedule():
    """Загружает расписание из Excel файла"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if os.path.exists(schedule_path):
            print(f"DEBUG: Загружаем расписание из {schedule_path}")

            # Читаем вкладку schedule
            df_schedule = pd.read_excel(schedule_path, sheet_name='schedule')

            # Исправляем названия колонок (убираем лишние пробелы)
            df_schedule.columns = df_schedule.columns.str.strip()

            print(f"DEBUG: Колонки schedule: {df_schedule.columns.tolist()}")
            print(f"DEBUG: Размер DataFrame: {df_schedule.shape}")
            print(f"DEBUG: Первые 10 строк расписания:")
            print(df_schedule.head(10))

            # Проверяем наличие необходимых колонок
            required_columns = ['День недели', 'Начало', 'Окончание', 'Вид спорта']
            missing_columns = [col for col in required_columns if col not in df_schedule.columns]
            if missing_columns:
                print(f"DEBUG: Отсутствуют колонки: {missing_columns}")
                return None

            # Проверяем, есть ли данные в DataFrame
            if df_schedule.empty:
                print("DEBUG: DataFrame пустой")
                return None

            # Преобразуем время в правильный формат
            print("DEBUG: Преобразуем время...")

            # Пробуем несколько форматов времени
            df_schedule['Начало'] = pd.to_datetime(df_schedule['Начало'], format='%H:%M:%S', errors='coerce').dt.time
            df_schedule['Окончание'] = pd.to_datetime(df_schedule['Окончание'], format='%H:%M:%S',
                                                      errors='coerce').dt.time

            # Если не сработало, пробуем формат без секунд
            if df_schedule['Начало'].isna().sum() > 0:
                df_schedule['Начало'] = pd.to_datetime(df_schedule['Начало'], format='%H:%M', errors='coerce').dt.time
                df_schedule['Окончание'] = pd.to_datetime(df_schedule['Окончание'], format='%H:%M',
                                                          errors='coerce').dt.time

            # Проверяем успешность преобразования времени
            print(f"DEBUG: Начало - пропущенные значения: {df_schedule['Начало'].isna().sum()}")
            print(f"DEBUG: Окончание - пропущенные значения: {df_schedule['Окончание'].isna().sum()}")

            # Удаляем строки с некорректным временем
            initial_count = len(df_schedule)
            df_schedule = df_schedule.dropna(subset=['Начало', 'Окончание'])
            print(f"DEBUG: Удалено строк с некорректным временем: {initial_count - len(df_schedule)}")

            # Заполняем пустые значения в виде спорта
            df_schedule['Вид спорта'] = df_schedule['Вид спорта'].fillna('По резерву')

            # Загружаем информацию об ответственных лицах
            print("DEBUG: Загружаем информацию об ответственных...")
            try:
                df_responsible = pd.read_excel(schedule_path, sheet_name='responsiblePersons')
                df_responsible.columns = df_responsible.columns.str.strip()
                print(f"DEBUG: Загружено {len(df_responsible)} записей ответственных")

                # Создаем словарь для быстрого доступа к ответственным лицам
                responsible_dict = {}
                for _, row in df_responsible.iterrows():
                    sport_type = row['Вид спорта']
                    if pd.notna(sport_type):
                        responsible_dict[sport_type] = {
                            'responsible': row['Ответственное лицо'] if pd.notna(row['Ответственное лицо']) else '',
                            'usernames': row['Имя пользователя'] if pd.notna(row['Имя пользователя']) else ''
                        }

                # Добавляем информацию об ответственных лицах в основное расписание
                df_schedule['Ответственное лицо'] = df_schedule['Вид спорта'].map(
                    lambda x: responsible_dict.get(x, {}).get('responsible', '')
                )
                df_schedule['Имя пользователя'] = df_schedule['Вид спорта'].map(
                    lambda x: responsible_dict.get(x, {}).get('usernames', '')
                )
            except Exception as e:
                print(f"DEBUG: Ошибка загрузки ответственных: {e}")
                df_schedule['Ответственное лицo'] = ''
                df_schedule['Имя пользователя'] = ''

            print(f"DEBUG: Успешно загружено {len(df_schedule)} записей расписания")
            print(f"DEBUG: Уникальные дни недели: {df_schedule['День недели'].unique()}")
            print(f"DEBUG: Уникальные виды спорта: {df_schedule['Вид спорта'].unique()}")

            # Проверяем данные для понедельника
            monday_data = df_schedule[df_schedule['День недели'] == 'Понедельник']
            print(f"DEBUG: Данные для понедельника: {len(monday_data)} записей")
            if not monday_data.empty:
                print("DEBUG: Пример данных понедельника:")
                for _, row in monday_data.iterrows():
                    print(f"  {row['Начало']}-{row['Окончание']} - {row['Вид спорта']}")

            return df_schedule
        else:
            print(f"DEBUG: Файл расписания {schedule_path} не найден")
            return None

    except Exception as e:
        print(f"Ошибка загрузки расписания: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_notice_list():
    """Загружает список пользователей для уведомлений"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if os.path.exists(schedule_path):
            df_notice = pd.read_excel(schedule_path, sheet_name='noticeList')
            notice_list = []

            # Обрабатываем все строки в колонке A
            for _, row in df_notice.iterrows():
                # Берем первую колонку
                username = str(row.iloc[0]).strip()
                # Проверяем, что это валидный username
                if (username and
                        username != 'nan' and
                        username != 'None' and
                        not username.isspace() and
                        len(username) > 1):  # Минимум 2 символа
                    notice_list.append(username)

            print(f"DEBUG: Загружен список уведомлений: {notice_list}")
            return notice_list
        else:
            print("DEBUG: Файл расписания не найден для загрузки noticeList")
            return []
    except Exception as e:
        print(f"Ошибка загрузки списка уведомлений: {e}")
        return []


async def send_notification(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Отправляет уведомления всем пользователям из списка"""
    notice_list = get_notice_list()

    if not notice_list:
        print("DEBUG: Список уведомлений пуст")
        return

    sent_count = 0
    for username in notice_list:
        try:
            # Убираем @ если есть
            clean_username = username.replace('@', '').strip()
            if clean_username:
                print(f"DEBUG: Пытаюсь отправить уведомление для @{clean_username}")

                # Пробуем отправить сообщение
                await context.bot.send_message(
                    chat_id=clean_username,
                    text=message,
                    parse_mode='HTML'
                )
                sent_count += 1
                print(f"DEBUG: ✅ Уведомление отправлено для @{clean_username}")
            else:
                print(f"DEBUG: ❌ Пустой username: {username}")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка отправки уведомления для {username}: {error_msg}")

            # Более детальный анализ ошибки
            if "Chat not found" in error_msg:
                print(f"   💡 Пользователь {username} не начал диалог с ботом или username неверный")
            elif "bot was blocked" in error_msg.lower():
                print(f"   💡 Пользователь {username} заблокировал бота")
            elif "user not found" in error_msg.lower():
                print(f"   💡 Пользователь {username} не найден")

    print(f"DEBUG: Всего отправлено уведомлений: {sent_count}/{len(notice_list)}")


# Получение временных слотов для конкретного дня
def get_time_slots_for_day(day_ru):
    schedule_df = load_schedule()
    if schedule_df is None:
        return []

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
    if schedule_df is None:
        return None

    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]

    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        current_slot = f"{start_str}-{end_str}"

        if current_slot == time_slot:
            result = {
                'sport_type': slot['Вид спорта'],
                'responsible': slot['Ответственное лицо'],
                'usernames': slot['Имя пользователя']
            }
            return result

    return None


# Создание кнопок для ответственных лиц
def create_responsible_buttons(responsible_text, usernames_text):
    buttons = []

    if not responsible_text or not usernames_text:
        return buttons

    # Разделяем ответственных лиц
    responsible_persons = [p.strip() for p in responsible_text.split('|')]
    username_list = [u.strip() for u in usernames_text.split('|')]

    for i, person in enumerate(responsible_persons):
        if i < len(username_list):
            username = username_list[i].replace('@', '').strip()
            if username and username != 'telegramuser' and username != 'username':
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
HALL_NAME = "💪 Спортивный зал НТЦ"


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
        [InlineKeyboardButton("💪 Забронировать зал", callback_data="select_date")],
        [InlineKeyboardButton("📅 Расписание", callback_data="schedule")],
        [InlineKeyboardButton("📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton("ℹ️ Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💪 Добро пожаловать в спортивный клуб НТЦ!\n\n"
        "Зал доступен для бронирования участникам клуба.\n"
        "Выберите действия:",
        reply_markup=reply_markup
    )


async def start_from_query(query):
    """Главное меню из callback query"""
    keyboard = [
        [InlineKeyboardButton("💪 Забронировать зал", callback_data="select_date")],
        [InlineKeyboardButton("📅 Расписание", callback_data="schedule")],
        [InlineKeyboardButton("📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton("ℹ️ Правила", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "💪 Добро пожаловать в спортивный клуб НТЦ!\n\n"
        "Зал доступен для бронирования участникам клуба.\n"
        "Выберите действия:",
        reply_markup=reply_markup
    )


def get_week_dates(start_date, days_count=7):
    """Возвращает список дат для недели начиная с start_date"""
    dates = []
    for i in range(days_count):
        date = start_date + datetime.timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        day_name_ru = RUSSIAN_DAYS[date.weekday()]
        dates.append((date_str, day_name_ru))
    return dates


def get_week_range_display(start_date):
    """Возвращает строку с диапазоном дат недели"""
    end_date = start_date + datetime.timedelta(days=6)
    start_str = start_date.strftime("%d.%m")
    end_str = end_date.strftime("%d.%m")
    return f"{start_str}-{end_str}"


def get_day_slots(date_str):
    """Возвращает все слоты для дня с информацией о доступности"""
    date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
    day_ru = RUSSIAN_DAYS[date_obj.weekday()]

    schedule_df = load_schedule()
    if schedule_df is None:
        return []

    print(f"DEBUG: Поиск слотов для {date_str} ({day_ru})")

    day_schedule = schedule_df[schedule_df['День недели'] == day_ru]
    print(f"DEBUG: Найдено {len(day_schedule)} записей для {day_ru}")

    slots = []
    for _, slot in day_schedule.iterrows():
        start_str = slot['Начало'].strftime('%H:%M')
        end_str = slot['Окончание'].strftime('%H:%M')
        time_slot = f"{start_str}-{end_str}"
        sport_type = slot['Вид спорта']

        available = is_slot_available(date_str, time_slot)
        booking_info = None
        if not available:
            booking_info = get_booking_info(date_str, time_slot)

        slots.append({
            'time_slot': time_slot,
            'sport_type': sport_type,
            'available': available,
            'booking_info': booking_info
        })

    print(f"DEBUG: Сформировано {len(slots)} слотов для {day_ru}")
    return slots


async def show_week_slots(query, week_offset=0):
    """Показывает все слоты на всю неделю с группировкой по дням"""
    today = datetime.datetime.now()
    start_date = today + datetime.timedelta(weeks=week_offset)

    # Определяем начало недели (понедельник)
    start_of_week = start_date - datetime.timedelta(days=start_date.weekday())

    # Формируем заголовок с выделенной информацией о неделе
    week_range = get_week_range_display(start_of_week)

    if week_offset == 0:
        week_info = "🏠 ТЕКУЩАЯ НЕДЕЛЯ"
        header = f"<b>📅 {week_info}</b>\n"
    else:
        week_number = week_offset + 1
        week_info = f"{week_number}-Я НЕДЕЛЯ"
        header = f"<b>📅 {week_info} ({week_range})</b>\n"

    message_text = f"💪 Доступные слоты для бронирования:\n{header}\n"

    keyboard = []
    week_dates = get_week_dates(start_of_week)

    print(f"DEBUG: Показываем неделю с {start_of_week.strftime('%d.%m.%Y')}")

    for date_str, day_name in week_dates:
        date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")

        # Пропускаем прошедшие даты
        if date_obj.date() < today.date():
            print(f"DEBUG: Пропускаем прошедшую дату {date_str}")
            continue

        # Получаем все слоты для этого дня
        day_slots = get_day_slots(date_str)

        if not day_slots:
            # День когда зал не работает
            print(f"DEBUG: Для {date_str} ({day_name}) нет слотов")
            continue

        # Добавляем заголовок дня в клавиатуру с иконкой календаря
        keyboard.append([InlineKeyboardButton(
            f"📅 {date_str} ({day_name})",
            callback_data="day_header"
        )])

        # ВСЕ СЛОТЫ ПОКАЗЫВАЕМ ОДИН ПОД ДРУГИМ
        for slot in day_slots:
            # Форматируем время с фиксированной шириной
            time_display = slot['time_slot']

            if slot['available']:
                if slot['sport_type'] == 'По резерву':
                    button_text = f"🟢 {time_display} - Любой вид спорта"
                else:
                    button_text = f"🟢 {time_display} - {slot['sport_type']}"

                # Каждый слот в отдельной строке
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"time_{date_str}_{slot['time_slot']}"
                )])
            else:
                # Занятые слоты - кнопка для просмотра информации
                booking_info = slot['booking_info']
                if booking_info:
                    if slot['sport_type'] == 'По резерву':
                        button_text = f"🔴 {time_display} - Занято"
                    else:
                        button_text = f"🔴 {time_display} - {slot['sport_type']}"

                    # Каждый слот в отдельной строке
                    keyboard.append([InlineKeyboardButton(
                        button_text,
                        callback_data=f"details_{date_str}_{slot['time_slot']}"
                    )])

    # Кнопки для навигации по неделям
    nav_buttons = []

    if week_offset > 0:
        nav_buttons.append(InlineKeyboardButton(
            "◀️ Неделя назад",
            callback_data=f"week_{week_offset - 1}"
        ))

    # Показываем кнопку следующей недели если есть доступные недели
    if week_offset < 3:  # 0=текущая, 1,2,3 = следующие 3 недели
        nav_buttons.append(InlineKeyboardButton(
            "Неделя вперёд ▶️",
            callback_data=f"week_{week_offset + 1}"
        ))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Добавляем легенду
    legend = (
        "\n📊 <b>Легенда:</b>\n"
        "🟢 - Свободно для брони\n"
        "🔴 - Уже занято\n\n"
        "💡 <i>Нажмите на зеленый слот для бронирования или на красный для информации</i>"
    )

    message_text += legend

    await query.edit_message_text(
        message_text,
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

    sport_keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"week_0")])
    reply_markup = InlineKeyboardMarkup(sport_keyboard)

    recommendation_text = f"\n\n🎯 <b>Рекомендуется:</b> {recommended_sport}" if recommended_sport else ""

    await query.edit_message_text(
        f"💪 Выберите вид спорта для {date_str} {time_slot}:{recommendation_text}",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


def get_sport_emoji(sport_type):
    """Возвращает эмодзи для вида спорта"""
    emoji_map = {
        "Бадминтон": "🏸",
        "Настольный теннис": "🏓",
        "Волейбол": "🏐",  # Общий волейбол
        "Волейбол (муж)": "🏐👨",  # Мужской волейбол
        "Волейбол (жен)": "🏐👩",  # Женский волейбол
        "Мини-футбол": "⚽",
        "Йога": "🧘",
        "Фитнес": "💪",
        "Теннис (большой)": "🎾",
        "Теннис (настольный)": "🏓",
        "Баскетбол": "🏀",
        "По резерву": "🟢"
    }
    return emoji_map.get(sport_type, "🎯")


async def confirm_booking(query, user_id, user_name, date_str, time_slot, sport_type):
    """Подтверждение бронирования"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить бронь", callback_data=f"confirm_{date_str}_{time_slot}_{sport_type}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"week_0")]
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


async def finalize_booking(query, user_id, user_name, date_str, time_slot, sport_type,
                           context: ContextTypes.DEFAULT_TYPE = None):
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
        'name': user_name,
        'username': username  # Сохраняем username
    }

    add_booking(user_id, booking_data)

    # Отправляем уведомление о новой брони
    notification_message = (
        f"🔔 Новая бронь!\n"
        f"📅 {date_str} {time_slot}\n"
        f"🎯 {sport_type}\n"
        f"👤 {user_name} (@{username if username else 'нет username'})"
    )

    if context:
        await send_notification(context, notification_message)
    else:
        print(f"DEBUG: Уведомление о брони: {notification_message}")

    await query.edit_message_text(
        f"✅ Бронь подтверждена!\n\n"
        f"📋 Детали:\n"
        f"• ID: {booking_id}\n"
        f"• Зал: {HALL_NAME}\n"
        f"• Дата: {date_str}\n"
        f"• Время: {time_slot}\n"
        f"• Вид спорта: {sport_type}\n\n"
        f"Ждем вас в клубе! 💪"
    )


async def show_contact_details(query, booking_info, date_str, time_slot):
    """Показывает детальную информацию с кликабельными ссылками"""

    contact_text = (
        f"🔍 Информация о брони:\n\n"
        f"⏰ <b>Время занято:</b>\n"
        f"📅 <b>Дата:</b> {date_str}\n"
        f"🕐 <b>Время:</b> {time_slot}\n"
        f"🎯 <b>Вид спорта:</b> {booking_info['sport_type']}\n"
        f"👤 <b>Имя:</b> {booking_info['name']}\n\n"
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
        InlineKeyboardButton("🔙 Назад к расписанию", callback_data=f"week_0")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        contact_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def cancel_specific_booking(query, user_id, booking_id, context: ContextTypes.DEFAULT_TYPE = None):
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

                # Отправляем уведомление об отмене брони
                notification_message = (
                    f"🔔 Отмена брони!\n"
                    f"📅 {booking['date']} {booking['time']}\n"
                    f"🎯 {booking['sport_type']}\n"
                    f"👤 {booking['name']} (@{booking.get('username', 'нет username')})"
                )

                if context:
                    await send_notification(context, notification_message)
                else:
                    print(f"DEBUG: Уведомление об отмене: {notification_message}")

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
            "Нажмите '💪 Забронировать зал' чтобы создать первую бронь!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💪 Забронировать зал", callback_data="select_date")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])
        )


async def show_weekly_schedule(query):
    """Показывает расписание на всю неделю в виде красивой таблицы"""
    schedule_df = load_schedule()
    if schedule_df is None:
        await query.edit_message_text(
            "❌ Расписание временно недоступно\nПопробуйте позже",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ])
        )
        return

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
                    schedule_text += f"│ 🟢 <code>{time_display:^11}</code> │ Любой вид спорта\n"
                else:
                    schedule_text += f"│ 🔵 <code>{time_display:^11}</code> │ {sport_display}\n"

            schedule_text += "└─────────────────────────────\n\n"

    schedule_text += "\n<code>🟢</code> - Любой вид спорта по резерву\n<code>🔵</code> - регулярное занятие\n\nНажмите на кнопку дня для деталей👇"

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
    if schedule_df is None:
        await query.edit_message_text(
            "❌ Расписание временно недоступно",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад к расписанию", callback_data="schedule")]
            ])
        )
        return

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
            schedule_text += f"🟢 <b>{time_display}</b> - Любой вид спорта\n"
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
            button_text = f"🟢 {time_slot} - Любой вид спорта"
        else:
            button_text = f"🔵 {time_slot} - {sport_type}"

        # Упрощаем callback_data - убираем пробелы и скобки
        day_simple = day_ru[:3]  # Берем первые 3 буквы дня
        time_simple = time_slot.replace(':', '').replace('-', '')  # Убираем : и -
        sport_simple = sport_type.split(' ')[0]  # Берем первое слово из вида спорта

        callback_data = f"slot_{day_simple}_{time_simple}"

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


async def show_sport_categories(query):
    """Показывает кнопки с видами спорта для выбора ответственных"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if not os.path.exists(schedule_path):
            await query.edit_message_text(
                "❌ Информация об ответственных лицах временно недоступна",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rules")]
                ])
            )
            return

        df_responsible = pd.read_excel(schedule_path, sheet_name='responsiblePersons')

        # Проверяем и исправляем названия колонок
        df_responsible.columns = df_responsible.columns.str.strip()
        print(f"DEBUG: Колонки responsiblePersons: {df_responsible.columns.tolist()}")

        # Проверяем наличие необходимой колонки
        if 'Вид спорта' not in df_responsible.columns:
            print("DEBUG: Колонка 'Вид спорта' не найдена в responsiblePersons")
            await query.edit_message_text(
                "❌ Ошибка в структуре данных об ответственных лицах",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rules")]
                ])
            )
            return

        # Создаем список уникальных видов спорта
        sport_types = []
        for _, row in df_responsible.iterrows():
            sport_type = row['Вид спорта']
            # Проверяем что значение не пустое и не NaN
            if pd.notna(sport_type) and str(sport_type).strip() and sport_type not in sport_types:
                sport_types.append(str(sport_type).strip())

        print(f"DEBUG: Найдено видов спорта: {sport_types}")

        if not sport_types:
            await query.edit_message_text(
                "❌ Нет данных об ответственных лицах",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="rules")]
                ])
            )
            return

        # Создаем кнопки для каждого вида спорта
        keyboard = []
        for i in range(0, len(sport_types), 2):
            row = []
            if i < len(sport_types):
                sport1 = sport_types[i]
                emoji1 = get_sport_emoji(sport1)
                row.append(InlineKeyboardButton(
                    f"{emoji1} {sport1}",
                    callback_data=f"responsible_{sport1.replace(' ', '_')}"  # Заменяем пробелы на подчеркивания
                ))
            if i + 1 < len(sport_types):
                sport2 = sport_types[i + 1]
                emoji2 = get_sport_emoji(sport2)
                row.append(InlineKeyboardButton(
                    f"{emoji2} {sport2}",
                    callback_data=f"responsible_{sport2.replace(' ', '_')}"  # Заменяем пробелы на подчеркивания
                ))
            if row:
                keyboard.append(row)

        # Добавляем кнопку для просмотра всех ответственных
        keyboard.append([InlineKeyboardButton("📋 Все ответственные", callback_data="responsible_list")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к правилам", callback_data="rules")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "👥 <b>ВЫБЕРИТЕ ВИД СПОРТА</b>\n\n"
            "Нажмите на кнопку с видом спорта, чтобы увидеть ответственных лиц:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Ошибка загрузки категорий спорта: {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            "❌ Ошибка загрузки информации об ответственных лицах",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="rules")]
            ])
        )


async def show_responsible_for_sport(query, sport_type_encoded):
    """Показывает ответственных лиц для конкретного вида спорта"""
    try:
        # Восстанавливаем оригинальное название вида спорта (заменяем подчеркивания обратно на пробелы)
        sport_type = sport_type_encoded.replace('_', ' ')

        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if not os.path.exists(schedule_path):
            await query.edit_message_text(
                "❌ Информация об ответственных лицах временно недоступна",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="sport_categories")]
                ])
            )
            return

        df_responsible = pd.read_excel(schedule_path, sheet_name='responsiblePersons')
        df_responsible.columns = df_responsible.columns.str.strip()

        # Ищем информацию для выбранного вида спорта
        sport_info = None
        for _, row in df_responsible.iterrows():
            current_sport = str(row['Вид спорта']).strip() if pd.notna(row['Вид спорта']) else ""
            if current_sport == sport_type:
                sport_info = row
                break

        if sport_info is None:
            await query.edit_message_text(
                f"❌ Нет информации об ответственных для {sport_type}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад к видам спорта", callback_data="sport_categories")]
                ])
            )
            return

        emoji = get_sport_emoji(sport_type)
        responsible_text = (
            f"{emoji} <b>{sport_type.upper()}</b>\n\n"
            f"👥 <b>Ответственные лица:</b>\n"
        )

        # Добавляем ответственных лиц
        if pd.notna(sport_info['Ответственное лицо']):
            responsible_text += f"{sport_info['Ответственное лицо']}\n\n"
        else:
            responsible_text += "Не указаны\n\n"

        responsible_text += "💬 <b>Для связи нажмите на кнопки ниже:</b>"

        # Создаем кнопки для ответственных лиц
        keyboard = []
        if pd.notna(sport_info['Ответственное лицо']) and pd.notna(sport_info['Имя пользователя']):
            keyboard = create_responsible_buttons(
                sport_info['Ответственное лицо'],
                sport_info['Имя пользователя']
            )

        # Добавляем кнопки навигации
        keyboard.append([InlineKeyboardButton("🔙 Назад к видам спорта", callback_data="sport_categories")])
        keyboard.append([InlineKeyboardButton("📋 Все ответственные", callback_data="responsible_list")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            responsible_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Ошибка загрузки ответственных для {sport_type_encoded}: {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            f"❌ Ошибка загрузки информации для {sport_type_encoded}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="sport_categories")]
            ])
        )


async def show_all_responsible(query):
    """Показывает всех ответственных лиц одним списком"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schedule_path = os.path.join(current_dir, SCHEDULE_FILE)

        if not os.path.exists(schedule_path):
            await query.edit_message_text(
                "❌ Информация об ответственных лицах временно недоступна",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="sport_categories")]
                ])
            )
            return

        df_responsible = pd.read_excel(schedule_path, sheet_name='responsiblePersons')
        df_responsible.columns = df_responsible.columns.str.strip()

        responsible_text = "👥 <b>ВСЕ ОТВЕТСТВЕННЫЕ ЛИЦА</b>\n\n"

        keyboard = []

        for _, row in df_responsible.iterrows():
            sport_type = str(row['Вид спорта']).strip() if pd.notna(row['Вид спорта']) else "Не указан"
            responsible = row['Ответственное лицо'] if pd.notna(row['Ответственное лицо']) else "Не указаны"
            usernames = row['Имя пользователя'] if pd.notna(row['Имя пользователя']) else ""

            emoji = get_sport_emoji(sport_type)
            responsible_text += f"{emoji} <b>{sport_type}</b>\n"
            responsible_text += f"   👤 {responsible}\n\n"

            # Создаем кнопки для ответственных
            if responsible != "Не указаны" and usernames:
                buttons = create_responsible_buttons(responsible, usernames)
                if buttons:
                    keyboard.extend(buttons)

        # Добавляем кнопки навигации
        keyboard.append([InlineKeyboardButton("📂 По видам спорта", callback_data="sport_categories")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к правилам", callback_data="rules")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            responsible_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Ошибка загрузки всех ответственных: {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            "❌ Ошибка загрузки информации об ответственных лицах",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="sport_categories")]
            ])
        )


async def show_rules(query):
    """Показывает правила из Excel файла с кнопками"""
    rules_text = load_rules()

    keyboard = [
        [InlineKeyboardButton("👥 Ответственные лица", callback_data="sport_categories")],
        [InlineKeyboardButton("✉️ Связь с разработчиком", url="https://t.me/RomanenkoIE")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        rules_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для получения своего chat_id"""
    user = update.effective_user
    chat_id = update.effective_chat.id

    message = (
        f"👤 <b>Ваши данные:</b>\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• Chat ID: <code>{chat_id}</code>\n"
        f"• Имя: {user.first_name or 'Не указано'}\n"
        f"• Фамилия: {user.last_name or 'Не указана'}\n"
        f"• Username: @{user.username or 'Не указан'}\n\n"
        f"📋 <b>Сообщите администратору:</b>\n"
        f"• Username: <code>@{user.username}</code>\n"
        f"• Chat ID: <code>{chat_id}</code>"
    )

    await update.message.reply_text(message, parse_mode='HTML')


async def test_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для проверки уведомлений"""
    user = update.effective_user

    test_message = (
        f"🔔 <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>\n\n"
        f"📅 Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"👤 От: {user.first_name or 'Тест'}\n"
        f"🆔 Chat ID: <code>{user.id}</code>\n\n"
        f"✅ Если вы видите это сообщение, система уведомлений работает!"
    )

    await send_notification(context, test_message)

    # Отправляем подтверждение обратно пользователю
    await update.message.reply_text(
        f"✅ Тестовое уведомление отправлено!\n"
        f"📊 Проверьте логи бота для деталей отправки.",
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
            print("DEBUG: Processing info_ button")
            data_parts = query.data.replace("info_", "").split("_")
            print(f"DEBUG: data_parts: {data_parts}")
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
            print("DEBUG: Processing slot_ button")
            data_parts = query.data.replace("slot_", "").split("_")
            print(f"DEBUG: data_parts: {data_parts}")
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

            slot_info = get_slot_info(day_ru, time_slot)

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
            print("DEBUG: Processing details_ button")
            data_parts = query.data.replace("details_", "").split("_")
            print(f"DEBUG: data_parts: {data_parts}")
            date_str = data_parts[0]
            time_slot = data_parts[1]

            booking_info = get_booking_info(date_str, time_slot)
            if booking_info:
                await show_contact_details(query, booking_info, date_str, time_slot)
            return

        elif query.data == "day_header":
            await query.answer("📅 Заголовок дня", show_alert=False)
            return

        # Для остальных кнопок
        await query.answer()

        print(f"DEBUG: Processing main button: {query.data}")

        # Сначала проверяем специальные кнопки, потом общие префиксы
        if query.data == "select_date":
            print("DEBUG: Calling show_week_slots")
            await show_week_slots(query, week_offset=0)

        elif query.data == "schedule":
            print("DEBUG: Calling show_weekly_schedule")
            await show_weekly_schedule(query)

        elif query.data == "back_to_main":
            print("DEBUG: Calling start_from_query")
            await start_from_query(query)

        elif query.data == "my_bookings":
            print("DEBUG: Calling show_user_bookings")
            await show_user_bookings(query, user_id)

        elif query.data == "rules":
            print("DEBUG: Calling show_rules")
            await show_rules(query)

        elif query.data == "sport_categories":
            print("DEBUG: Calling show_sport_categories")
            await show_sport_categories(query)

        elif query.data == "responsible_list":
            print("DEBUG: Calling show_all_responsible")
            await show_all_responsible(query)

        # Теперь проверяем префиксы
        elif query.data.startswith("week_"):
            print("DEBUG: Processing week_ button")
            # Обработка переключения недель
            week_offset = int(query.data.replace("week_", ""))
            await show_week_slots(query, week_offset)

        elif query.data.startswith("day_"):
            print("DEBUG: Processing day_ button")
            # Обработка кнопок дней недели
            day_ru = query.data.replace("day_", "")
            await show_day_schedule(query, day_ru)

        elif query.data.startswith("responsible_"):
            print("DEBUG: Processing responsible_ button")
            # Извлекаем вид спорта из callback_data
            sport_type_encoded = query.data.replace("responsible_", "")
            print(f"DEBUG: sport_type_encoded: {sport_type_encoded}")
            await show_responsible_for_sport(query, sport_type_encoded)

        elif query.data.startswith("time_"):
            print("DEBUG: Processing time_ button")
            data_parts = query.data.replace("time_", "").split("_")
            print(f"DEBUG: time data_parts: {data_parts}")
            date_str = data_parts[0]
            time_slot = data_parts[1]

            if is_slot_available(date_str, time_slot):
                await select_sport_type(query, user_id, user_name, date_str, time_slot)
            else:
                await query.edit_message_text(
                    "❌ Это время уже занято!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад к расписанию", callback_data=f"week_0")]
                    ])
                )

        elif query.data.startswith("sport_"):
            print("DEBUG: Processing sport_ button")
            data_parts = query.data.replace("sport_", "").split("_")
            print(f"DEBUG: sport data_parts: {data_parts}")
            date_str = data_parts[0]
            time_slot = data_parts[1]
            sport_type = data_parts[2]

            if is_slot_available(date_str, time_slot):
                await confirm_booking(query, user_id, user_name, date_str, time_slot, sport_type)
            else:
                await query.edit_message_text(
                    "❌ Это время только что заняли!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад к расписанию", callback_data=f"week_0")]
                    ])
                )

        elif query.data.startswith("confirm_"):
            print("DEBUG: Processing confirm_ button")
            data_parts = query.data.replace("confirm_", "").split("_")
            print(f"DEBUG: confirm data_parts: {data_parts}")
            date_str = data_parts[0]
            time_slot = data_parts[1]
            sport_type = data_parts[2]

            if is_slot_available(date_str, time_slot):
                await finalize_booking(query, user_id, user_name, date_str, time_slot, sport_type, context)
            else:
                await query.edit_message_text(
                    "❌ Это время только что заняли!\nВыберите другое время.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад к расписанию", callback_data=f"week_0")]
                    ])
                )

        elif query.data.startswith("cancel_"):
            print("DEBUG: Processing cancel_ button")
            # Обработка отмены конкретной брони
            booking_id = query.data.replace("cancel_", "")
            await cancel_specific_booking(query, user_id, booking_id, context)

        else:
            print(f"DEBUG: Unknown button: {query.data}")
            await query.answer("❌ Неизвестная команда")

    except Exception as e:
        print(f"ERROR in handle_button: {e}")
        import traceback
        print("FULL TRACEBACK:")
        traceback.print_exc()
        # Пытаемся ответить на запрос, если он еще валиден
        try:
            await query.answer("❌ Произошла ошибка, попробуйте еще раз")
        except:
            pass  # Игнорируем ошибку, если запрос уже невалиден


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Простой обработчик ошибок"""
    logging.error(f"Exception while handling an update: {context.error}")


def main():
    """Основная функция запуска бота"""
    print("=" * 50)
    print(f"🚀 ЗАПУСК БОТА - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Загружаем данные
    load_data()

    print(f"📊 Загружено пользователей с бронями: {len(bookings)}")
    total_bookings = sum(len(user_bookings) for user_bookings in bookings.values())
    print(f"📊 Всего броней: {total_bookings}")
    print(f"📊 Занятых слотов: {len(occupied_slots)}")

    try:
        # Создаем Application
        global application
        application = (
            Application.builder()
            .token(TOKEN)
            .pool_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .build()
        )

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("myid", get_my_id))
        application.add_handler(CommandHandler("test_notify", test_notify))

        # Обработчики callback кнопок
        application.add_handler(CallbackQueryHandler(handle_button))

        # Обработчик ошибок
        application.add_error_handler(error_handler)

        print("✅ Бот инициализирован!")

        # Запускаем polling локально или webhook на Render
        if os.getenv('RENDER'):
            print("🌐 Режим: Webhook (Render)")
            # На Render бот будет запущен через Flask
        else:
            print("🔄 Режим: Polling (локально)")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    if application is None:
        return jsonify({"status": "error", "message": "Bot not initialized"}), 500

    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        # Создаем контекст для обработки
        async def process_update():
            await application.process_update(update)

        # Запускаем обработку асинхронно
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_update())

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def home():
    return "🤖 Sport Bot is running on Render!"


@app.route('/health')
def health():
    return "OK", 200


@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    try:
        webhook_url = f"https://{request.host}/webhook"
        result = application.bot.set_webhook(webhook_url)
        return f"Webhook set to: {webhook_url}<br>Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@app.route('/get_webhook_info')
def get_webhook_info():
    """Получение информации о webhook"""
    try:
        info = application.bot.get_webhook_info()
        return f"Webhook info: {info}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    main()
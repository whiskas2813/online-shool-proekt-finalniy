import telebot
from telebot import types
import config
import sqlite3
import re
import random  # Добавляем модуль random

# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN)

# --- Смайлики для настроения ---
HAPPY_EMOJIS = ["😄", "😊", "🥳", "😎", "👍"]
SAD_EMOJIS = ["😔", "😟", "😕", "🤔"]
EDIT_EMOJIS = ["✏️", "📝", "✍️"]
ADD_EMOJIS = ["➕", "✨", "🌟"]
DAY_EMOJIS = ["☀️", "🌤️", "🌥️", "🌦️", "🌧️", "🌨️", "🌈"]  # Для дней недели

# --- Глобальные переменные ---
admin_mode = False
editing_day = None
editing_lesson_index = None
current_user_id = None
lesson_to_delete_id = None
current_schedule = {}
editing_lesson_id = None
edit_state = None

# --- Инициализация базы данных ---
def create_database():
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            lesson TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_database()

# --- Функции для работы с базой данных ---
def get_schedule_from_db():
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, day, lesson, time FROM schedule")
    schedule_data = cursor.fetchall()
    conn.close()

    schedule = {}
    for lesson_id, day, lesson, time in schedule_data:
        if day not in schedule:
            schedule[day] = []
        schedule[day].append({"id": lesson_id, "lesson": lesson, "time": time})
    return schedule

def add_lesson_to_db(day, lesson, time):
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schedule (day, lesson, time) VALUES (?, ?, ?)", (day, lesson, time))
    conn.commit()
    conn.close()

def update_lesson_in_db(lesson_id, day, lesson_name, lesson_time):
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE schedule SET day = ?, lesson = ?, time = ? WHERE id = ?", (day, lesson_name, lesson_time, lesson_id))
    conn.commit()
    conn.close()

def delete_lesson_from_db(lesson_id):
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

# Проверяет, есть ли пользователь в базе. Если нет, добавляет его.
def register_user(user_id):
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        print(f"User {user_id} registered.")
    conn.close()

# ----- Функции администратора -----

def is_admin(message):
    return message.from_user.id in [message.chat.id]

def show_admin_panel(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Показать расписание " + random.choice(HAPPY_EMOJIS))
    item2 = types.KeyboardButton("Редактировать расписание " + random.choice(EDIT_EMOJIS))
    item3 = types.KeyboardButton("Выйти из режима админа " + random.choice(SAD_EMOJIS))
    markup.add(item1, item2, item3)
    bot.send_message(chat_id, "Вы в режиме администратора. Что будем делать? 😉", reply_markup=markup)

def edit_schedule_start(chat_id):
    markup = types.InlineKeyboardMarkup()
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for i, day in enumerate(days):
        markup.add(types.InlineKeyboardButton(f"{day} {DAY_EMOJIS[i % len(DAY_EMOJIS)]}", callback_data=f"set_day:{day}"))
    bot.send_message(chat_id, "Выберите день недели для магии: ✨", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_day:"))
def set_day_callback(call):
    global editing_day
    editing_day = call.data.split(":")[1]
    bot.answer_callback_query(call.id, f"Вы выбрали {editing_day}! Отлично! {random.choice(HAPPY_EMOJIS)}")

    show_lessons_for_day_buttons(call.message.chat.id)

def show_lessons_for_day_buttons(chat_id):
    global current_schedule
    current_schedule = get_schedule_from_db()
    lessons = current_schedule.get(editing_day, [])

    markup = types.InlineKeyboardMarkup()
    for i in range(1, 10):  # Кнопки для уроков 1-9
        lesson_text = f"Урок {i}"
        if i <= len(lessons):
            lesson_text += f" ({lessons[i-1]['lesson']})" # Показывать название урока, если есть
        markup.add(types.InlineKeyboardButton(lesson_text, callback_data=f"set_lesson:{i}"))

    markup.add(types.InlineKeyboardButton(f"➕ Добавить урок {random.choice(ADD_EMOJIS)}", callback_data="add_lesson"))
    bot.send_message(chat_id, f"Выберите урок для {editing_day}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_lesson:"))
def set_lesson_callback(call):
    global editing_lesson_index, edit_state, editing_lesson_id

    editing_lesson_index = int(call.data.split(":")[1]) - 1
    bot.answer_callback_query(call.id, "Начинаем редактирование! " + random.choice(EDIT_EMOJIS))

    global current_schedule
    current_schedule = get_schedule_from_db()
    lessons = current_schedule.get(editing_day, [])

    if editing_lesson_index < len(lessons):
        editing_lesson_id = lessons[editing_lesson_index]['id']
        bot.send_message(call.message.chat.id, f"Введите новое название урока {random.choice(EDIT_EMOJIS)}:")
        edit_state = "name"
    else:
        editing_lesson_id = None
        bot.send_message(call.message.chat.id, f"Введите название нового урока {random.choice(ADD_EMOJIS)}:")
        edit_state = "name"

    bot.register_next_step_handler(call.message, process_lesson_data)

def process_lesson_data(message, lesson_name=None):
    global edit_state, editing_lesson_id, editing_day

    if edit_state == "name":
        lesson_name = message.text
        bot.send_message(message.chat.id, f"Теперь введите время урока {random.choice(EDIT_EMOJIS)}:")
        edit_state = "time"
        bot.register_next_step_handler(message, process_lesson_data, lesson_name=lesson_name)
    elif edit_state == "time":
        lesson_time = message.text

        # Объявляем переменные как глобальные перед использованием
        global current_schedule
        current_schedule = get_schedule_from_db()

        # Проверяем, не выходной ли день
        if editing_day not in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]:
            bot.send_message(message.chat.id, "Это выходной день! " + random.choice(SAD_EMOJIS))
            return

        # Проверяем, не пустое ли время

        if editing_lesson_id:
            update_lesson_in_db(editing_lesson_id, editing_day, lesson_name, lesson_time)
            bot.send_message(message.chat.id, "Урок обновлен! " + random.choice(HAPPY_EMOJIS))
        else:
            add_lesson_to_db(editing_day, lesson_name, lesson_time)
            bot.send_message(message.chat.id, "Урок добавлен! " + random.choice(HAPPY_EMOJIS))

        # Сбрасываем состояния
        edit_state = None
        editing_lesson_index = None
        editing_lesson_id = None

        show_lessons_for_day_buttons(message.chat.id)

# ----- Функции для пользователей -----

def get_schedule_string():
    schedule = get_schedule_from_db()
    schedule_string = ""
    for day, lessons in schedule.items():
        schedule_string += f"<b>{day}:</b>\n"
        if lessons:
            for lesson in lessons:
                schedule_string += f"  - {lesson['lesson']} ({lesson['time']})\n"
        else:
            schedule_string += "  - Выходной\n"
    return schedule_string

# ----- Обработчики сообщений -----
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    register_user(user_id)
    global current_user_id
    current_user_id = user_id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Показать расписание " + random.choice(HAPPY_EMOJIS))
    item2 = types.KeyboardButton("Войти как преподаватель " + random.choice(EDIT_EMOJIS))
    markup.add(item1, item2)
    bot.send_message(message.chat.id, f"Привет! Я бот онлайн-школы, готов помочь! {random.choice(HAPPY_EMOJIS)} Что хочешь сделать?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.startswith("Показать расписание"))
def show_schedule(message):
    schedule_string = get_schedule_string()
    bot.send_message(message.chat.id, schedule_string, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text.startswith("Войти как преподаватель"))
def admin_login(message):
    bot.send_message(message.chat.id, "Введите пароль администратора:")
    bot.register_next_step_handler(message, process_admin_password)

def process_admin_password(message):
    if message.text == config.ADMIN_PASSWORD:
        global admin_mode
        admin_mode = True
        show_admin_panel(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Неверный пароль. " + random.choice(SAD_EMOJIS))

# ----- Обработчики для админ-панели -----

@bot.message_handler(func=lambda message: admin_mode and message.text.startswith("Выйти из режима админа"))
def admin_logout(message):
    global admin_mode
    admin_mode = False
    bot.send_message(message.chat.id, "Вы вышли из режима администратора. " + random.choice(SAD_EMOJIS), reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: admin_mode and message.text.startswith("Показать расписание"))
def admin_show_schedule(message):
    schedule_string = get_schedule_string()
    bot.send_message(message.chat.id, schedule_string, parse_mode="HTML")

@bot.message_handler(func=lambda message: admin_mode and message.text.startswith("Редактировать расписание"))
def admin_edit_schedule(message):
    edit_schedule_start(message.chat.id)

# ----- Обработчик любого текста (кроме команд) -----
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Я вас не понимаю. Используйте кнопки или команды. " + random.choice(SAD_EMOJIS))

# Запуск бота
if __name__ == '__main__':
    # Инициализация расписания из базы данных при запуске бота
    current_schedule = get_schedule_from_db()
    bot.polling(none_stop=True)
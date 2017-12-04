"""
Created by anthony on 12.11.17
state_service
"""
from components.automata import *
from services import user_service, task_service
from config.state_config import State
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from utils import handler_utils
import g

def states():
    return {
        State.START: start_state,
        State.SELECT_LANG: select_lang_state,
        State.ALL_TASKS: all_tasks_state,
        State.NEW_TASK: new_task_state,
        State.VIEW_TASK: view_task_state,
        State.EDIT_DATE: edit_date_state,
        State.ERROR: error_state
    }


def start_state(bot, update, context, lang):
    chat = update.message.chat
    user = user_service.create_or_get_user(chat)

    reply_msg = 'Hello'
    if user:
        reply_msg += ', ' + user.get_first_name()

    update.message.reply_text(reply_msg)


def select_lang_state(bot, update, context, lang):
    chat = update.message.chat
    user = user_service.create_or_get_user(chat)

    reply_msg = 'Hello'
    if user:
        reply_msg += ', ' + user.get_first_name() + '\n'
    reply_msg += "Select language:"
    keyboard = [[InlineKeyboardButton("Русский", callback_data='rus'),
                 InlineKeyboardButton("English", callback_data='eng')],
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(reply_msg, reply_markup=reply_markup)
    g.automata.set_state(update.message.chat.id, State.ALL_TASKS)


def lang_button(bot, update):
    query = update.callback_query

    g.automata.set_lang(query.message.chat_id, query.data)
    if query.data == 'eng':
        bot.edit_message_text(text="Selected english language",
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
    if query.data == 'rus':
        bot.edit_message_text(text="Выбран русский язык",
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)


def all_tasks_state(bot, update, context, lang):
    chat = update.message.chat

    user = user_service.create_or_get_user(chat)
    user_tasks = task_service.find_tasks_by_user_id(user.get_id())

    tasks_to_show = [f'[{t.get_id()}] {t.get_description()}' for t in user_tasks]

    first_name = user.get_first_name()
    if 0 == len(tasks_to_show):
        if g.automata.get_lang(chat.id) == 'eng':
            update.message.reply_text(f'{first_name}, you don\'t have any tasks yet')
            update.message.reply_text('Just write me something to create a new one :)')
        elif g.automata.get_lang(chat.id) == 'rus':
            update.message.reply_text(f'{first_name}, у вас еще нет задач')
            update.message.reply_text('Просто напишите мне что-нибудь чтобы создать :)')

    else:
        if g.automata.get_lang(chat.id) == 'rus':
            update.message.reply_text(first_name + ', ваши задачи:\n' + '\n'.join(tasks_to_show))
        if g.automata.get_lang(chat.id) == 'eng':
            update.message.reply_text(first_name + ', here are your tasks:\n' + '\n'.join(tasks_to_show))


def new_task_state(bot, update, context, lang):
    chat = update.message.chat
    new_task = task_service.create_task(update)

    if new_task:
        context[CONTEXT_TASK] = new_task
        if g.automata.get_lang(chat.id) == 'eng':
            reply_on_success = f'task with id "{new_task.get_id()}" has been created!'
        if g.automata.get_lang(chat.id) == 'rus':
            reply_on_success = f'задача с id "{new_task.get_id()}" была создана!'
        user = user_service.create_or_get_user(chat)
        if user:
            reply_on_success = user.get_first_name() + ', ' + reply_on_success

        update.message.reply_text(reply_on_success.capitalize())


def view_task_state(bot, update, context, lang):
    args = update.message.text.split()
    task_id = args[1]

    chat = update.message.chat
    user = user_service.create_or_get_user(chat)

    task = task_service.find_task_by_id_and_user_id(task_id, user.get_id())
    if task:
        context[CONTEXT_TASK] = task

        task_descr = task.get_description()

        update.message.reply_text(f'[{task_id}]: {task_descr}')

    else:
        first_name = user.get_first_name()
        if g.automata.get_lang(chat.id) == 'eng':
            update.message.reply_text(f'Sorry, {first_name}, I couldn\'t find task with id "{task_id}"')
        if g.automata.get_lang(chat.id) == 'rus':
            update.message.reply_text(f'Извините, {first_name}, не могу найти задачу с таким id "{task_id}"')

def edit_date_state(bot, update, context, lang):
    args = update.message.text.split()
    datetime_args = args[1:]
    latest_task = context[CONTEXT_TASK]
    chat = update.message.chat
    if latest_task:
        user_id = update.message.chat.id
        latest_task_by_user = task_service.find_task_by_id_and_user_id(latest_task.get_id(), user_id)

        if latest_task_by_user:
            parsed_datetime = handler_utils.parse_date_msg(datetime_args)
            latest_task_by_user.set_next_remind_date(parsed_datetime)
            if g.automata.get_lang(chat.id) == 'eng':
                update.message.reply_text(f'Setting date to {parsed_datetime} for task:')
            if g.automata.get_lang(chat.id) == 'rus':
                update.message.reply_text(f'Поставлена дата {parsed_datetime} для задачи:')
            update.message.reply_text(f'[{latest_task.get_id()}]: {latest_task.get_description()}')
            return

    update.message.reply_text(f'Sorry, I could not find that task')


def error_state(bot, update, context, lang):
    lastest_task_id = context[CONTEXT_TASK].get_id()
    command_trace = [c.name for c in context[CONTEXT_COMMANDS]]
    chat = update.message.chat
    if g.automata.get_lang(chat.id) == 'eng':
        update.message.reply_text(f'Error. Latest task id: {lastest_task_id}. Command trace: {command_trace}')
    if g.automata.get_lang(chat.id) == 'rus':
        update.message.reply_text(f'Ошибка. id последней задачи: {lastest_task_id}. Command trace: {command_trace}')


import requests
import logging

import xmltodict
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

KESSEL_URI = "24/10561"
KESSEL_ZUSTAND_URI = "24/10561/0/11109/2002"
KESSEL_STOERMELDUNG_URI = "24/10561/0/0/14265"
KESSEL_DRUCK_URI = "24/10561/0/0/12180"


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ function that gives out current heater status"""
    ret_status = requests.get(
        f"http://{context.bot_data['hostname']}/user/var/{KESSEL_ZUSTAND_URI}")
    ret_pressure = requests.get(
        f"http://{context.bot_data['hostname']}/user/var/{KESSEL_DRUCK_URI}")
    if ret_status.status_code != 200 or ret_pressure.status_code != 200:
        await update.message.reply_text(f'o_O {update.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich ... ')
        return

    status = xmltodict.parse(ret_status.content)['eta']['value']['@strValue']
    pressure = xmltodict.parse(ret_pressure.content)[
        'eta']['value']['@strValue']
    started = "Ein" if context.bot_data['started'] else "Aus"
    await update.message.reply_text(f'Hallo {update.effective_user.first_name}, die Heizung ist {status}geschaltet bei einem Kesseldruck von {pressure} Bar. Die Benachrichtung ist aktuell {started}geschaltet ...')


async def fehler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ function that gives out current error if existing """
    ret_error = requests.get(
        f"http://{context.bot_data['hostname']}/user/errors/{KESSEL_URI}")
    if ret_error.status_code != 200:
        await update.message.reply_text(f'o_O {update.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich ... ')
        return

    d_ret = xmltodict.parse(ret_error.content)
    if 'error' in d_ret['eta']['errors']['fub']:
        error = d_ret['eta']['errors']['fub']['error']
        await update.message.reply_text(f"Hallo {update.effective_user.first_name}, seit [{error['@time']}] besteht ein(e) {error['@priority']}\
            mit folgender Nachricht: {error['@msg']}, --> {error['#text']}")
    else:
        await update.message.reply_text(f'Hallo {update.effective_user.first_name}, aktuell liegen keine Fehler oder Störungen an der Heizung vor ...')


async def check_for_error_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ async routine to run in interval to check if the heater has a warning or an error """

    ret = requests.get(
        f"http://{context.bot_data['hostname']}/user/errors/{KESSEL_URI}")
    if ret.status_code != 200:
        await context.bot.send_message(f'o_O {context.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich, die Anwendung wird daher gestoppt, erneut starten via /start ... ')
        STARTED = False

    d_ret = xmltodict.parse(ret.content)

    error = context.bot_data['error']
    logging.info(f'error : {error}')
    # ERROR FOUND
    if 'error' in d_ret['eta']['errors']['fub']:

        # NEW ERROR FOUND: found error in heater and the error is not like stored error or no error
        if d_ret['eta']['errors']['fub']['error'] != error:
            error = d_ret['eta']['errors']['fub']['error']
            logging.info(
                f"[{error['@time']}] {error['@priority']}: {error['@msg']} \n\t--> {error['#text']}")
            await context.bot.send_message(context.job.chat_id, text=f"{error['@priority']} | [{error['@time']}]: {error['@msg']} --> {error['#text']}")

        # ERROR STILL EXISTING: stored error == error in heater
        elif d_ret['eta']['errors']['fub']['error'] == error:
            logging.info("error still existing ...")

    # ERROR SOLVED: error is set, but no error message from heater
    elif error != {}:
        logging.info(f"{error['@msg']}: --> solved ...")
        await context.bot.send_message(context.job.chat_id, text=f"Problem: {error['@msg']} gelöst! Wohoo")
        error = {}

    # NO ERROR
    else:
        logging.info("No error found ...")

    context.bot_data['error'] = error


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def hilfe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ function to send help text """
    help_text = f'''Hallo {update.effective_user.first_name},\n dir stehen folgende Befehle zur Verfügung:\n\
/start -> started den Benachrichtigungsdienst\n\
/stop -> stoppt den Benachrichtungsdienst\n\
/fehler -> gibt dir aus ob aktuell ein Fehler besteht\n\
/status -> gibt dir aktuelle Informationen zum Kessel\n\
/hilfe -> gibt diese Hilfe aus'''

    await update.message.reply_text(help_text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ start interval job to check for errors or warnings"""
    interval = 30
    start_in = 1
    data = {}
    context.bot_data['error'] = {}
    # check if connection is available ...
    if requests.get(f"http://{context.bot_data['hostname']}/user/menu").status_code != 200:
        update.message.reply_text(
            f'o_O {update.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich, bitte fix den Bug und rufe erneut /start auf ... ')
        return

    chat_id = update.effective_message.chat_id

    # if job is already running give message and return
    if context.job_queue.get_jobs_by_name(chat_id):
        await update.effective_message.reply_text(f'Heizungsbenachrichtung ist bereits aktiv. Sie kann via /stop gestopt werden ...')
        return
    # start job
    context.job_queue.run_repeating(callback=check_for_error_job,
                                    interval=interval,
                                    first=start_in,
                                    last=None,
                                    data=data,
                                    chat_id=chat_id,
                                    name=str(chat_id)
                                    )
    context.bot_data['started'] = True
    await update.effective_message.reply_text(f'Hallo {update.effective_user.first_name}, die Heizungsbenachrichtung wurde gestartet. Um die Benachrichtigung zu stoppen nutze /stop ...')


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ stops the asyncronous job """
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    context.bot_data['started'] = False

    await update.message.reply_text(f'''
        Hallo {update.effective_user.first_name}, die Heizungsbenachrichtung wurde gestoppt. 
        Um die Benachrichtigung zu erneut zu starten nutze /start ...
        ''')


async def cal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Sends a message with three inline buttons attached. """
    keyboard = [
        [
            InlineKeyboardButton("Zeige den aktuellen Kalender", callback_data="1"),
            InlineKeyboardButton("Wählen", callback_data="2"),
        ],
        [InlineKeyboardButton("Option 3", callback_data="3")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)


async def cal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")
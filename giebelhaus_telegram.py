

from typing import List, Optional
import requests
import logging
import datetime

import xmltodict
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

KESSEL_URI = "24/10561"
KESSEL_ZUSTAND_URI = "24/10561/0/11109/2002"
KESSEL_STOERMELDUNG_URI = "24/10561/0/0/14265"
KESSEL_DRUCK_URI = "24/10561/0/0/12180"

MENU = "0"
MENU_STATUS = "1"
MENU_ERROR = "2"
MENU_CHOOSE = "3"
MENU_CALENDAR = "4"

MENU_NOTIFICATION = "5"
MENU_NOTIFCATION_START = "6"
MENU_NOTIFCATION_STOP = "7"

# Stages
START_ROUTES, END_ROUTES = range(2)


def add_notification_user(user, engine):
    """ write updated userlist if a user attaches or detaches to/from list"""
    try:
        users.insert().values(name="jack", fullname="Jack Jones")
    except Exception as E:
        logging.warning(
            "could not remove {chat_id} from notify_users list ...\n{E}")


def del_notification_user(user, engine):
    try:
        pass
    except Exception as E:
        logging.warning(
            "could not remove {chat_id} from notify_users list ...\n{E}")


def get_error(hostname) -> Optional[List]:
    """
    gets the error from the heater

    Returns:
        optional(list): returns none if a connection error occurs an empty list if no error is present, else a list of errors
    """
    ret_error = requests.get(
        f"http://{hostname}/user/errors/{KESSEL_URI}")
    if ret_error.status_code != 200:
        return None

    d_ret = xmltodict.parse(ret_error.content)
    try:
        error = d_ret['eta']['errors']['fub']['error']
        if isinstance(error, list):
            return error
        if isinstance(error, dict):
            return [error]
    except:
        return []


##########################
# INTERACTIONS ENDPOINTS #
##########################

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ function that gives out current heater status"""

    ret_status = requests.get(
        f"http://{context.bot_data['hostname']}/user/var/{KESSEL_ZUSTAND_URI}")

    ret_pressure = requests.get(
        f"http://{context.bot_data['hostname']}/user/var/{KESSEL_DRUCK_URI}")

    query = update.callback_query
    chat_id = update.effective_message.chat_id

    if ret_status.status_code != 200 or ret_pressure.status_code != 200:
        await query.edit_message_text(
            text=f'o_O {update.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich ... ')
        return ConversationHandler.END

    status = xmltodict.parse(ret_status.content)['eta']['value']['@strValue']
    pressure = xmltodict.parse(ret_pressure.content)[
        'eta']['value']['@strValue']
    started = "Ein" if chat_id in context.bot_data["notify_users"] else "Aus"

    await query.answer()
    keyboard = [[InlineKeyboardButton("zurück", callback_data=MENU)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f'Hallo {update.effective_user.first_name}, die Heizung ist {status}geschaltet bei einem Kesseldruck von {pressure} Bar. Die Benachrichtung ist aktuell {started}geschaltet ...', reply_markup=reply_markup)
    return START_ROUTES


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ function that gives out current error if existing """

    query = update.callback_query
    error = get_error(context.bot_data['hostname'])

    if error is None:
        await query.edit_message_text(
            text=f'o_O {update.effective_user.first_name}: Die Verbindung zur Heizung ist aktuell nicht möglich ... ')
        return ConversationHandler.END
    elif error == []:
        text = f'Hallo {update.effective_user.first_name}, aktuell liegen keine Fehler oder Störungen an der Heizung vor ...'
    else:
        text = f"Hallo {update.effective_user.first_name},"
        for e in error:
            text += f"seit [{e['@time']}] besteht ein(e) {e['@priority']} mit folgender Nachricht: {e['@msg']}, --> {e['#text']}\n"

    # show back menu end text output
    await query.answer()
    keyboard = [[InlineKeyboardButton("zurück", callback_data=MENU)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text, reply_markup=reply_markup)
    return START_ROUTES


async def check_for_error_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ async routine to run in interval to check if the heater has a warning or an error """

    current_error = get_error(context.bot_data['hostname'])

    last_error = context.bot_data['error']
    logging.debug(f"async task got: {str(current_error)}")
    message = ""

    if current_error is None:
        # something is wrong with the heater API
        pass

    # new response == old response
    if current_error == last_error:
        logging.info("error|health state did not change ...")

    # if new response != old response and new response no error, write a message that the problem is solved
    elif current_error != last_error and current_error == []:
        logging.info(f"{str(last_error)}: --> solved ...")
        message = f"Problem: {last_error['@msg']} gelöst! Wohoo"
    else:
        for e in current_error:
            message += f"{e['@priority']} | [{e['@time']}]: {e['@msg']} --> {e['#text']}"

    if message != "":
        # send this text to each chat_id in bot_data notify_user_file
        for chat_id in context.bot_data['notify_users']:
            await context.bot.send_message(chat_id, text=message)

    context.bot_data['error'] = current_error


#################
# NOTIFICATIONS #
#################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ start interval job to check for errors or warnings"""

    context.bot_data['error'] = {}

    chat_id = update.effective_message.chat_id
    query = update.callback_query

    # if user is already running give message and return
    if chat_id in context.bot_data["notify_users"]:
        text = f'die Benachrichtung war schon aktiviert, daher bleibt alles beim alten.'
        logging.warning(
            f'{update.effective_user.username} tried to activate messages twice, skipped activation ...')
    else:
        # start job
        text = f'die Benachrichtung wurde aktiviert.'
        context.bot_data['notify_users'].append(chat_id)
        add_notification_user(
            userlist=context.bot_data['notify_users'], filename=context.bot_data['notify_user_file'])

    # show back menu end text output
    await query.answer()
    keyboard = [[InlineKeyboardButton("zurück", callback_data=MENU)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text, reply_markup=reply_markup)
    return START_ROUTES


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ stops the asyncronous job """

    query = update.callback_query
    chat_id = update.effective_message.chat_id

    text = f'Die Heizungsbenachrichtungen wurde gestoppt.'
    context.bot_data['notify_users'].remove(chat_id)
    del_notification_user(
        userlist=context.bot_data['notify_users'], filename=context.bot_data['notify_user_file'])

    # show back menu end text output
    await query.answer()
    keyboard = [[InlineKeyboardButton("zurück", callback_data=MENU)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text, reply_markup=reply_markup)
    return START_ROUTES


################
# INLINE MENUS #
################

async def notification_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    chat_id = update.effective_message.chat_id
    query = update.callback_query
    await query.answer()
    if chat_id in context.bot_data['notify_users']:
        text = "Benachrichtigungen sind aktuell für diesen chat aktiviert."
        keyboard = [
            [
                InlineKeyboardButton(
                    "Benachrichtigungen stoppen", callback_data=MENU_NOTIFCATION_STOP),
                InlineKeyboardButton("zurück", callback_data=MENU),
            ]
        ]

    else:
        text = "Benachrichtigungen sind aktuell für diesen chat deaktiviert."
        keyboard = [
            [
                InlineKeyboardButton(
                    "Benachrichtigungen starten", callback_data=MENU_NOTIFCATION_START),
                InlineKeyboardButton("zurück", callback_data=MENU),
            ]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text, reply_markup=reply_markup)
    return START_ROUTES


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Sends a message with three inline buttons attached. """
    keyboard = [
        [
            InlineKeyboardButton("Zeige den aktuellen Kalender",
                                 callback_data=MENU_CALENDAR),
            InlineKeyboardButton(
                "Tag(e) für Heizdienst Wählen", callback_data=MENU_CHOOSE),
        ],
        [
            InlineKeyboardButton("aktueller Status",
                                 callback_data=MENU_STATUS),
            InlineKeyboardButton("aktuelle Fehler", callback_data=MENU_ERROR),
        ],
        [
            InlineKeyboardButton("Benachrichtigungsdienst",
                                 callback_data=MENU_NOTIFICATION)
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # comming from smb calling /menu
    if update.message:
        await update.message.reply_text("Was willst du tun?:", reply_markup=reply_markup)
    # comming from smb going back in menu
    else:
        query = update.callback_query
        await query.edit_message_text(text="Und jetzt?:", reply_markup=reply_markup)
    return START_ROUTES


async def choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show choose date CallbackQuery"""
    query = update.callback_query
    chat_id = update.effective_message.chat_id

    text = "An welchem Tag möchtest du den Heizungsdienst übernehmen?"
    keyboard = []
    for i in range(7):
        day = datetime.date.today() + datetime.timedelta(days=i)
        day.strftime(format="%A: %d.%m.%y")
        keyboard.append([InlineKeyboardButton(str(day.strftime(format='%A: %d.%m.%y')), callback_data="ZVEN")])
    keyboard.append([InlineKeyboardButton("zurück", callback_data=MENU)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return START_ROUTES


async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")
    return START_ROUTES

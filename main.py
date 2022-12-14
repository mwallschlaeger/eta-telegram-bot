
import argparse
import logging
import os
import sys

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler
import giebelhaus_telegram as gt


def configure_logging(debug, filename=None):
    """ just some logging handling """
    if filename is None:
        if debug:
            logging.basicConfig(
                format='%(asctime)s %(message)s', level=logging.DEBUG)
        else:
            logging.basicConfig(
                format='%(asctime)s %(message)s', level=logging.INFO)
    else:
        if debug:
            logging.basicConfig(filename=filename,
                                format='%(asctime)s %(message)s', level=logging.DEBUG)
        else:
            logging.basicConfig(filename=filename,
                                format='%(asctime)s %(message)s', level=logging.INFO)


def main():
    """ main function get called first """
    parser = argparse.ArgumentParser()

    parser.add_argument("-H", "--hostname", default=os.environ.get("ETA_HOSTNAME"), dest="hostname", required=False,
                        help="hostname of the target heater, if not set uses ETA_HOSTNAME env var, good luck ...", metavar='')
    parser.add_argument(
        "-l", "--log", help="Redirect logs to a given file in addition to the console.", metavar='')
    parser.add_argument("-t", "--telegram-token", default=os.environ.get("ETA_TELEGRAM_TOKEN"), dest="telegram_token", required=False,
                        help="telegram bot token ...", type=str, metavar='')
    parser.add_argument("-n", "--notification-user-file", default=os.environ.get("ETA_TELEGRAM_NOTIFICATION_USERS_FILE"),
                        dest="notify_user_file", required=True, help="path to file which stores used who activated notification service, got created if not existing ...")
    parser.add_argument("-i", "--interval", default=30, dest="interval",
                        required=False, help="interval of requests to the heater in seconds ..")

    parser.add_argument("-v", "--verbose", action='store_true',
                        help="Enable verbose logging")
    args = parser.parse_args()

    debug = False
    if args.verbose:
        debug = True

    if args.log:
        logfile = args.log
        configure_logging(debug, logfile)
    else:
        configure_logging(debug)
        logging.debug("debug mode enabled")

    telegram_token = args.telegram_token

    # Setup Telegram Bot
    logging.info("initialize telegram bot connection")
    app = ApplicationBuilder().token(telegram_token).build()

    app.bot_data['hostname'] = args.hostname
    app.bot_data['notify_user_file'] = args.notify_user_file
    userlist = []
    try:
        with open(args.notify_user_file) as f:
            userlist = f.readlines()
            userlist = [int(line.rstrip()) for line in userlist]
    except:
        logging.error("Could not load userlist file ...")
        sys.exit(1)
    app.bot_data["notify_users"] = userlist
    app.bot_data["error"] = []

    app.job_queue.run_repeating(callback=gt.check_for_error_job,
                                interval=args.interval,
                                first=1,
                                last=None,
                                data={}
                                )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", gt.menu)],
        states={
            gt.START_ROUTES: [
                CallbackQueryHandler(
                    gt.status, pattern="^" + gt.MENU_STATUS + "$"),
                CallbackQueryHandler(
                    gt.error, pattern="^" + gt.MENU_ERROR + "$"),
                CallbackQueryHandler(gt.menu, pattern="^" + gt.MENU + "$"),
                CallbackQueryHandler(gt.notification_menu,
                                     pattern="^" + gt.MENU_NOTIFICATION + "$"),
                CallbackQueryHandler(
                    gt.start, pattern="^" + gt.MENU_NOTIFCATION_START + "$"),
                CallbackQueryHandler(
                    gt.stop, pattern="^" + gt.MENU_NOTIFCATION_STOP + "$"),

                # CallbackQueryHandler(gt.choose_date, pattern="^" + gt.MENU_CHOOSE + "$"),
                # CallbackQueryHandler(gt.show_calendar, pattern="^" + gt.MENU_CALENDAR + "$"),
            ],
            gt.END_ROUTES: [
                CallbackQueryHandler(gt.error, pattern="^" + "ERROR" + "$"),
                #CallbackQueryHandler(end, pattern="^" + str(TWO) + "$"),
            ],
        },
        fallbacks=[CommandHandler("menu", gt.menu)],
    )
    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == '__main__':
    main()

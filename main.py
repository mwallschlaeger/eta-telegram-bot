
import argparse
import logging
import os

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import giebelhaus_telegram as gt


def configure_logging(debug, filename=None):
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
    parser = argparse.ArgumentParser()

    parser.add_argument("-H", "--hostname", default=os.environ.get("ETA_HOSTNAME"), dest="hostname", required=False,
                        help="hostname of the target heater, if not set uses ETA_HOSTNAME env var, good luck ...", metavar='')
    parser.add_argument(
        "-l", "--log", help="Redirect logs to a given file in addition to the console.", metavar='')
    parser.add_argument("-t", "--telegram-token", default=os.environ.get("ETA_TELEGRAM_TOKEN"), dest="telegram_token", required=False,
                        help="telegram bot token ...", type=str, metavar='')
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
    app.bot_data['started'] = False
    app.bot_data['hostname'] = args.hostname
    app.add_handler(CommandHandler("status", gt.status))
    app.add_handler(CommandHandler("fehler", gt.fehler))
    app.add_handler(CommandHandler("start", gt.start))
    app.add_handler(CommandHandler("stop", gt.stop))
    
    app.add_handler(CommandHandler("cal", gt.cal_menu))
    app.add_handler(CallbackQueryHandler(gt.cal))
    app.add_handler(CommandHandler("hilfe", gt.hilfe))
    app.run_polling()


if __name__ == '__main__':
    main()
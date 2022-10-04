# eta-telegram-bot

mini python telegram bot to get status and warnings from eta heater. The bot uses the [ETA REST API](ETA-RESTful-v1.1.pdf) and the famous [python-telegram-bot library](https://python-telegram-bot.org). 

# Install Guide

requires:
* python >= 3.9
* Telegram_BOT including Token, ask the botfather

install dependencies via:
```
pip install requirements.txt
pip install python-telegram-bot --pre
```

run via:
```
python main.py -t $TELEGRAM_BOT_TOKEN -H IP_OF_THE_HEATER --notification-user-file users.txt # notification filed used to store users which have attached to notification service after restart ... 
```

# current features
* get current status: on|off and boiler pressure
* get current error: shows an error or warning occured in the heater
* notification: writes a messages as soon as an error or warning occures or is resolved

## TODOS
* force remove ashes from boiler
* calendar organisation to organise empty ashes process

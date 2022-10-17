#!/bin/bash

FOLDER="/home/pi/eta-telegram-bot"

source "$FOLDER/load-config.sh"
source "$FOLDER/venv/bin/activate"
python "$FOLDER/main.py" -n "/home/pi/users.txt"

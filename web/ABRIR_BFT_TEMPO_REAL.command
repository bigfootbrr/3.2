#!/bin/zsh
cd -- "$(dirname -- "$0")"

# Inicia a interface web de tempo real em http://127.0.0.1:8765
exec /Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python interface_tempo_real.py

#!/usr/bin/env bash

virtualenv2 venv

python src/helper/rank_gen.py ranks.json src

(source .env && FLASK_APP=src/server.py flask run --port 63083 )

#!/usr/bin/env bash

source bin/activate

FLASK_APP=server.py flask run --port 63083

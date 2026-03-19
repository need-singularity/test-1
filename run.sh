#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python run_loop.py "$@"

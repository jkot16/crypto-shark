#!/bin/bash

# Step 1: Ask the user for interval in minutes
read -p "How often (in minutes) should check_crypto.py run? [e.g. 10] " interval

# Validate input
if ! [[ "$interval" =~ ^[0-9]+$ ]] || [ "$interval" -le 0 ]; then
  echo "Invalid input. Aborting."
  exit 1
fi

# Step 2: Get full path to check_crypto.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/check_crypto.py"
LOG_FILE="$SCRIPT_DIR/check_crypto.log"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "File check_crypto.py not found at: $PYTHON_SCRIPT"
  exit 1
fi

# Step 3: Build cron line (directly runs Python and logs output)
CRON_LINE="*/$interval * * * * /usr/bin/env python3 \"$PYTHON_SCRIPT\" >> \"$LOG_FILE\" 2>&1"

# Step 4: Add to crontab (removing previous instance of this exact script path)
( crontab -l 2>/dev/null | grep -v "$PYTHON_SCRIPT" ; echo "$CRON_LINE" ) | crontab -

# Step 5: Confirm
echo "Cron job added to run check_crypto.py every $interval minutes."
crontab -l | grep "$PYTHON_SCRIPT"

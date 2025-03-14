#!/usr/bin/env bash

# Cleanup
rm -f user_input.txt.aqua.json
rm -f user_input.txt
rm -f agent_log.txt.aqua.json
rm -f agent_log.txt
rm -f aqua_secured_logs.zip

# User
echo "I'm looking for a flight from Berlin to San Francisco on May 30 2025. Let me choose the available flights. Output the flight data in JSON format" > user_input.txt

node notarize.js user_input.txt
node notarize.js --sign cli user_input.txt --cred credentials_user.json

# Agent
allow_list="0x0198a1e5c8b96d9b5cff91e68b0d73e1b73b61c3"

output=$(node verify.js -v user_input.txt)
echo "$output"
echo "Checking if the wallet address is allowed"
echo "$output" | grep $allow_list
echo "exit status $?"
python travel_agent_simple.py
node notarize.js agent_log.txt
node notarize.js agent_log.txt --link user_input.txt
node notarize.js agent_log.txt --sign cli --cred credentials_agent.json

# Zip artifacts
echo "Create zip archive for user_input.txt.aqua.json user_input.txt agent_log.txt.aqua.json agent_log.txt"
zip -r aqua_secured_logs.zip user_input.txt.aqua.json user_input.txt agent_log.txt.aqua.json agent_log.txt

#!/bin/bash
cd dialog_agent_service
gunicorn -b 0.0.0.0:$DIALOGAGENTSERVICE_PORT -w $NUM_WORKERS "app:app"

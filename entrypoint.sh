#!/bin/bash
cd dialog_agent_service
gunicorn -b 0.0.0.0:$DIALOG_AGENT_SERVICE_PORT -w $NUM_WORKERS "app:app"

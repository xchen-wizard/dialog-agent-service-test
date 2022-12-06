# dialog-agent-service
A python Flask service to handle backend integration with a dialog agent.

## Setup
1. Install dependencies
```commandline
poetry install
```
2. Set env vars in a .env file. Please reach out to author for example values
3. Run app locally
```commandline
poetry run python dialog_agent_service/app.py
```

## Tests
### Unit Tests
```commandline
poetry run python -m pytest tests/unit
```
### Integration Tests
TBD

# dialog-agent-service
A python Flask service to handle backend integration with a dialog agent.

## Setup
1. Install dependencies
```commandline
poetry install
```
2. Set env vars in a .env file. See `./config/.env`
3. Run app locally
```commandline
cd dialog_agent_service
poetry run python app.py
```

## Tests
### Unit Tests
First, set the path to the .env file. See `./config/.env` for an example or put a .env file in the root dir.
```commandline
export ENV_FILE=path/to/env/file
```
Then
```commandline
poetry run python -m pytest tests/unit
```
### Integration Tests
Set the path to the .env file.
```commandline
poetry run python -m pytest tests/integration
```

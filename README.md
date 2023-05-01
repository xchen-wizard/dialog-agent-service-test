# dialog-agent-service
A python Flask service to handle backend integration with a dialog agent.

## Requirements
- python 3.10
- poetry
- mongodb
- mysql


## Setup
1. Install dependencies
```commandline
poetry install
```
2. Copy and set the required ENV vars in the .env file
```commandline 
cd config
cp .env.example .env
```
3. Google Auth
```commandline 
gcloud auth application-default login
```
4. Run app locally with the dev server
```commandline
cd dialog_agent_service
ENV_FILE=../config/.env poetry run python app.py
```
### MongoDB Setup
1. Install MongoDB 5.x
```commandline
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

2. Dump Staging Data (optional)
```commandline
mongodump --uri=mongodb+srv://mongwizstaging:{password}@stage-mongodb.ceogg.mongodb.net --excludeCollection=messages --db=spt`
```

*Replace {password} with the proper value. Ask a dev to give you this value.

3. Restore Staging Data
```commandline
mongorestore -h localhost:27017 -d spt dump/spt
```

## Tests
### Unit Tests
First, set the path to the .env file.
```commandline
export ENV_FILE=./config/.env
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

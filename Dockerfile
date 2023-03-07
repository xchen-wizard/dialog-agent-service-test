
ARG SERVICE_NAME="dialog-agent-service"

# Execute tests
FROM python:3.10.5 AS tester
ARG SERVICE_NAME
ENV SERVICE_NAME="$SERVICE_NAME"
ENV DIALOGFLOW_PROJECT_ID="campaign-prototype-oxtt"
ENV DIALOGFLOW_ENVIRONMENT="draft"
ENV MONGO_UUID_NAMESPACE="499f044c-3f69-436e-b52d-d2bdba0d4772"
ENV UNITTEST="true"
ENV AGENT_TYPE='dialogflow'
ENV GOOGLE_APPLICATION_CREDENTIALS=''
COPY pyproject.toml ./
COPY poetry.lock ./
COPY dialog_agent_service ./dialog_agent_service
COPY tests ./tests
RUN pip3 install poetry==1.1.15 && \
  poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi
RUN poetry run python -m pytest tests/unit

# Docker image to run
FROM python:3.10.5
ARG SERVICE_NAME
ENV SERVICE_NAME="$SERVICE_NAME"
WORKDIR /$SERVICE_NAME
COPY pyproject.toml ./
COPY --from=tester poetry.lock ./
COPY dialog_agent_service ./dialog_agent_service
COPY entrypoint.sh ./
RUN pip3 install poetry==1.4.0 && \
  poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-dev
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

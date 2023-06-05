import dialog_agent_service.conversational_agent.task_handlers as th
import logging
from dialog_agent_service.utils.utils import camel_to_snake


def task_handler(task: str, **kwargs):
    handler = getattr(th, f"handle_{camel_to_snake(task)}", th.default_handler)
    try:
        return handler(task=task, **kwargs)
    except Exception as e:
        logging.exception(f'Exception thrown in one of the task handlers: {e}')
        return th.default_handler(msg=f"Exception: {e}", task=task)


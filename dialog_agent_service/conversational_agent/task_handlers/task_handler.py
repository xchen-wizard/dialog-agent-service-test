import dialog_agent_service.conversational_agent.task_handlers as th
import logging
from dialog_agent_service.utils.utils import camel_to_snake
from dialog_agent_service.das_exceptions import DASException


def task_handler(task: str, **kwargs):
    handler = getattr(th, f"handle_{camel_to_snake(task)}", th.default_handler)
    try:
        return handler(task=task, **kwargs)
    except DASException as e:
        return th.default_handler(msg=f"{e.__class__.__name__} {e}", task=task)
    except Exception:
        return th.default_handler(msg='Unknown Exception thrown.', task=task)


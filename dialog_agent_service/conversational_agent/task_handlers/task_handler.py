import dialog_agent_service.conversational_agent.task_handlers as th
import re
import logging

pattern_1 = re.compile('(.)([A-Z][a-z]+)')
pattern_2 = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(name):
    return pattern_2.sub(
        r'\1_\2',
        pattern_1.sub(r'\1_\2', name)
    ).lower()


def task_handler(task: str, **kwargs):
    handler = getattr(th, f"handle_{camel_to_snake(task)}", th.default_handler)
    try:
        return handler(task=task, **kwargs)
    except Exception as e:
        logging.exception(f'Exception thrown in one of the task handlers: {e}')
        return th.default_handler(msg=f"Exception: {e}", task=task)


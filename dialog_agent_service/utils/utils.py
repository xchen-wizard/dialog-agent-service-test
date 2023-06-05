import re
import inspect

pattern_1 = re.compile('(.)([A-Z][a-z]+)')
pattern_2 = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(name):
    return pattern_2.sub(
        r'\1_\2',
        pattern_1.sub(r'\1_\2', name)
    ).lower()


def handler_to_task_name():
    """
    Convert handler name, e.g. handle_task_snake_case to
    :return: TaskSnakeCase
    """
    name = inspect.stack()[1].function
    task_snake_case = name[7:]
    split_name = task_snake_case.split("_")
    return "".join(ele.title() for ele in split_name)

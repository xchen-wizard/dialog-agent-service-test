def default_handler(**kwargs):
    msg = kwargs.get('msg', 'task handler not implemented')
    task = kwargs['task']
    return {'task': task, 'response': f"Issue: {msg}", 'handoff': True}

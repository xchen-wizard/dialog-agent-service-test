def default_handler(**kwargs):
    msg = kwargs.get('msg', 'task handler not implemented')
    return {'response': f"Issue: {msg}", 'handoff': True}

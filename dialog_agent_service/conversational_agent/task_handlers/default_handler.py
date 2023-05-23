def default_handler(**kwargs):
    msg = kwargs.get('msg', 'task handler not implemented')
    return {'response': "Issue: {msg}", 'handoff': True}

def namespace(*values):
    if values:
        tokens = list(values[:-1]) + [str(values[-1])]
        return '.'.join(tokens)
    return ''


def denamespace(namespaced_value):
    tokens = namespaced_value.split('.')
    return '.'.join(tokens[:-1]), tokens[-1]

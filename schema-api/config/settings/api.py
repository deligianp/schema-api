from config.env import env

DISABLE_TASK_SCHEDULING = env.bool('SCHEMA_API_DISABLE_TASK_SCHEDULING', False)

TASK_API = {
    'TASK_API_CLASS': env.str('SCHEMA_API_TASK_API_CLASS', None),
    'GET_TASK_ENDPOINT': env.str('SCHEMA_API_TASK_API_GET_ENDPOINT', None),
    'CREATE_TASK_ENDPOINT': env.str('SCHEMA_API_TASK_API_CREATE_ENDPOINT', None),
    'DB_TASK_STATUS_TTL_SECONDS': env.int('SCHEMA_API_TASK_API_STATUS_TTL_SECONDS', 5)
}

CONTEXT_MINIMUM_RESOURCES = {
    'CPU': env.int('SCHEMA_API_CONTEXT_MIN_CPU', 1),
    'RAM_GB': env.int('SCHEMA_API_CONTEXT_MIN_RAM_GB', 1),
    'TASKS': env.int('SCHEMA_API_CONTEXT_MIN_TASKS', 1),
    'ACTIVE_TASKS': env.int('SCHEMA_API_CONTEXT_MIN_ACTIVE_TASKS', 1),
    'PROCESS_TIME_SECONDS': env.int('SCHEMA_API_CONTEXT_MIN_PROCESS_TIME_SECONDS', 10 * 60)
}

TASK_DEFAULT_RESOURCES = {
    'CPU': env.int('SCHEMA_API_TASK_DEFAULT_CPU', 1),
    'RAM_GB': env.int('SCHEMA_API_TASK_DEFAULT_RAM_GB', 1),
    'DISK_GB': env.int('SCHEMA_API_TASK_DEFAULT_DISK_GB', 5)
}

CONTEXT_NAME_SLUG_PATTERN = env.str('SCHEMA_API_CONTEXT_NAME_SLUG_PATTERN', None)
CONTEXT_NAME_SLUG_PATTERN_VIOLATION_MESSAGE = env.str('SCHEMA_API_CONTEXT_NAME_SLUG_PATTERN_VIOLATION_MESSAGE', None)

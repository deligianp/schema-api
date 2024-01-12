"""
ASGI config for schema_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os
from config.env import env

from django.core.asgi import get_asgi_application

deployment_environment = env.str('SCHEMA_API_DEPLOYMENT', 'dev')
"""Run administrative tasks."""
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.environments.' + deployment_environment)

application = get_asgi_application()

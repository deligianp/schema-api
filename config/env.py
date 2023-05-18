import os

import environ

root = environ.Path(__file__) - 2
env = environ.Env()
environ.Env.read_env(os.path.join(root, '.env'))

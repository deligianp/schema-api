# Installation guide

This document describes the requirements and instructions for deploying **schema-api**.

## Prerequisites

**Schema-api** is a Python REST API that aims to authorize and delegate containerized tasks to an existing Task Execution API. It is built using the Django ORM and Django REST framework. This sections provides details about the requirements that need to be satisfied.

### Python version

**Schema-api** was developed and tested using Python 3.10.

### Task execution API

In order for jobs to be run, an underlying API is required to which accepted tasks by **schema-api**, can be delegated to. **Schema-api** is natively designed to support the Task Execution Schema (TES) API standard, proposed by GA4GH. However, **schema-api** is designed in a way that supports the definition of any other possible API that supports basic task management actions.

### Relational Database Management System

To efficiently manage and record task execution requests, **schema-api** also requires access to a RDBMS. Any RDBMS from the [ones supported by Django](https://docs.djangoproject.com/en/4.1/ref/databases/#databases) can be used.

## Installation

0. Initially, get access to the code of **schema-api** by cloning this repository. After cloning the repository, navigate to the root directory of the project, where the manage.py file is located.
    
    It is also advised to use a Python `virtualenv` for the installation of the API.
1. The first step, is to install the Python package requirements for **schema-api**. This can be done with:
    
    `pip install -r requirements.txt`
2. After the packages get installed, run the following command to generate a unique key for the deployment:

    `python manage.py generate_secret_key`

    Keep the generated key to a temporary file since it's going to be needed in the following steps.
3. Use the provided settings template file to create a local/deployment-specific settings file.

    `cp schema_api/local_settings.py.template schema_api/local_settings.py`

    Then use a text editor to open and edit the produced `local_settings.py` file:
   1. Set `DEBUG` to `True` if **schema-api** is being deployed in a development environment, otherwise `False`.
   2. Set `ALLOWED_HOSTS` with a Python list of the acceptable domain names that **schema-api** can accept requests. For development environments, this can be just an empty list, `[]`.
   3. Set `SECRET_KEY` with the key produced in step 2.
   4. Fill the required information for the `default` RDBMS (every value as a string), as described in the [Django documentation](https://docs.djangoproject.com/en/4.1/ref/databases/#databases). An example is provided for the case of a local Postgres database:
      
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': 'schema_api_db',
                    'USER': 'django',
                    'PASSWORD': 'django',
                    'HOST': 'localhost',
                    'PORT': '5432'
                }
            }
        ***Note:*** *It is possible that also a database driver package is required for service-database communication. For the example above, that package is `psycopg2-binary`, which can be installed with:*
        
        `pip install psycopg2-binary`
   5. Finally, provide the required information about the task execution API
        - Protocol: the store type in which files used in the tasks are stored
        - Task GET endpoint: API endpoint on which task status can be retrieved from
        - Task POST endpoint: API endpoint on which new tasks can be submitted
      An example for a task execution API that conforms with TES is provided as an example:
      
                TASK_APIS = {
                    'TES': {
                        'PROTOCOL': 'ftp',
                        'TASK_GET_ENDPOINT': 'https://tesk.api.com/v1/tasks',
                        'TASK_POST_ENDPOINT': 'http://tesk.api.com/v1/tasks',
                    }
                }

4. With the settings passed on `local-settings.py`, **schema-api** should now be able to access the data base and create the required database schema. To achieve this the required migrations must be inferred using:

    `python manage.py makemigrations`

5. Apply the rendered migrations with:

    `python manage.py migrate`

6. At this point **schema-api** should be properly configured to accept tasks requests. If **schema-api** is deployed in a development environment, Django's provided server can be run with:

    `python manage.py runserver`

## Testing

After successfully running **schema-api**, to quickly test its functionality, `curl` can be used.

To create a really simple task, run the following command:

            curl -X POST "127.0.01:8000/api/tasks/" -H "accept: application/json" -H "Content-Type: application/json" -d '{"name": "Sample task", "executors": [{"command":["echo","test"],"image":"alpine"}]}'

**schema-api** should respond with a UUID that can be used to reference the task. e.g. `eba061bc-e071-456f-adc7-289c71a6fc2f`

Use this UUID to poll **schema-api** and get the status of the task

            curl "127.0.01:8000/api/tasks/eba061bc-e071-456f-adc7-289c71a6fc2f/"

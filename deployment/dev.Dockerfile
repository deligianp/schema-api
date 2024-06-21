FROM python:3.11

EXPOSE 80

RUN pip3 install pipenv

RUN mkdir -p /schema-api

WORKDIR /schema-api

COPY Pipfile Pipfile

RUN pipenv lock && pipenv requirements > requirements.txt && pip3 install -r requirements.txt --no-cache-dir

ENTRYPOINT ["python3", "manage.py"]
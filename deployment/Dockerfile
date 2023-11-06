FROM python:3.11

ENV SCHEMA_API_DEPLOYMENT production

RUN mkdir -p /schema-api

WORKDIR /schema-api

EXPOSE 8000

RUN pip3 install pipenv

COPY Pipfile.lock Pipfile.lock

RUN pipenv requirements > requirements.txt && pip3 install -r requirements.txt --no-cache-dir

RUN pip3 install psycopg2-binary gunicorn uvicorn

COPY . .

CMD ["gunicorn", "--bind", ":8000", "-k", "uvicorn.workers.UvicornWorker", "schema_api.asgi"]
FROM python:3.6.5-alpine3.7

RUN mkdir /app
WORKDIR /code
ADD requirements.txt /app/

RUN apk update && \
    apk add postgresql-libs && \
    apk add --virtual .build-deps gcc musl-dev postgresql-dev
RUN pip install -r /app/requirements.txt --no-cache-dir
RUN apk --purge del .build-deps

ADD . /app/

COPY ./scripts/gunicorn.sh /gunicorn.sh
RUN sed -i 's/\r//' /gunicorn.sh
RUN chmod +x /gunicorn.sh
#RUN chown django /gunicorn.sh

COPY ./scripts/start-celerybeat.sh /start-celerybeat.sh
RUN sed -i 's/\r//' /start-celerybeat.sh
RUN chmod +x /start-celerybeat.sh


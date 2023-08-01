# pull official base image
FROM python:3.11.1-alpine

# set work directory
WORKDIR /usr/src

# set environment variables
ENV SECRET_KEY="" \
    DEBUG=""\
    DJANGO_ALLOWED_HOSTS=""\
    CELERY_BROKER=""\
    CELERY_BACKEND=""

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . ./server/
COPY ./config/config.yaml ./server/config/config.yaml

CMD python3 -m server.main

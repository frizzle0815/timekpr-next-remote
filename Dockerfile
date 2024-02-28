FROM python:3.8-slim-buster
ENV PYTHONUNBUFFERED=1
RUN mkdir /app
COPY requirements.txt /app/
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY . /app/
CMD ["gunicorn", "-c", "gunicorn.conf.py", "timekpr_next_web:app"]

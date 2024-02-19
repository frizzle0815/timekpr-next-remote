FROM python:3.8-slim-buster
ENV PYTHONUNBUFFERED=1
RUN mkdir /app
COPY requirements.txt /app/
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY . /app/
CMD ["python3", "./timekpr-next-web.py"]

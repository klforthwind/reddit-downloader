FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . .
COPY gallery-dl.conf /etc/gallery-dl.conf

RUN pip install -U gallery-dl
RUN pip install -r requirements.txt

CMD ["python", "./main.py"]

FROM python:3.10
WORKDIR /docker
COPY requirements.txt /docker/
RUN pip install -r requirements.txt
COPY . /docker
CMD python jenovabot.py
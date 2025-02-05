FROM python:3.10
WORKDIR /docker
COPY . .
RUN pip install -r requirements.txt
CMD python jenovabot.py
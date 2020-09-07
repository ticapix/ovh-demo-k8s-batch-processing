FROM python:3

RUN pip install kubernetes==11.0.0

COPY monitor.py .
ENTRYPOINT ["./monitor.py"]

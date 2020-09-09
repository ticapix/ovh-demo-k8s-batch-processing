FROM python:3

RUN pip install kubernetes==11.0.0

COPY autoscale_nodepool.py .
ENTRYPOINT ["./autoscale_nodepool.py"]

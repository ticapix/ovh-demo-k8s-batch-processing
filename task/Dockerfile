FROM jrottenberg/ffmpeg:4.1-ubuntu

RUN apt update
RUN apt install --no-install-recommends --yes bc
RUN apt install --no-install-recommends --yes jq
RUN apt install --no-install-recommends --yes python3-pip
RUN apt install --no-install-recommends --yes python3-setuptools
RUN rm -rf /var/cache/apt/archives

RUN pip3 install --upgrade pip
RUN pip3 install python-swiftclient==3.10.0
RUN pip3 install python-keystoneclient==4.1.0

COPY transcode.sh .
ENTRYPOINT ["./transcode.sh"]

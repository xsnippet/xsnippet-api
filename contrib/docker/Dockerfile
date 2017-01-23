FROM python:latest
MAINTAINER The XSnippet Team <dev@xsnippet.org>

COPY . /app
WORKDIR /app
RUN pip install .

ENV XSNIPPET_API_SETTINGS=/etc/xsnippet-api.conf

EXPOSE 8000
ENTRYPOINT ["python", "-m", "xsnippet_api"]

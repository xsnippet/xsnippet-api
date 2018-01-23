FROM python:latest
MAINTAINER The XSnippet Team <dev@xsnippet.org>

COPY . /app
RUN pip install /app && rm -rf /app

ENV XSNIPPET_API_SETTINGS=/etc/xsnippet-api.conf

EXPOSE 8000
ENTRYPOINT ["python", "-m", "xsnippet.api"]

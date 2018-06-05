FROM python:latest

COPY . /app
WORKDIR /app
RUN mkdir dist && pip wheel --wheel-dir dist .


FROM python:slim
MAINTAINER The XSnippet Team <dev@xsnippet.org>

COPY --from=0 /app/dist /dist
RUN ls -la /dist && pip install --no-cache-dir --no-index --find-links=/dist xsnippet-api && rm -rf /dist
ENV XSNIPPET_API_SETTINGS=/etc/xsnippet-api.conf

EXPOSE 8000
ENTRYPOINT ["python", "-m", "xsnippet.api"]

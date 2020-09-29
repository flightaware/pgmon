FROM alpine:3.5

LABEL maintainer="Adam Schumacher <adam.schumacher@flightaware.com>" \
    org.label-schema.schema-version="1.0" \
    org.label-schema.name="pgmon.flightaware.com" \
    org.label-schema.vcs-url="https://github.com/flightaware/pgmon" \
    org.label-schema.description="pgmon"


RUN apk update && \
    apk add --no-cache --virtual build-deps gcc python3 python3-dev musl-dev && \
    apk add postgresql-dev && \
    apk add py3-psycopg2 && \
	apk add py3-requests && \
    apk add zabbix-utils


COPY destination /usr/local/pgmon/lib/destination/
COPY database /usr/local/pgmon/lib/database/
COPY *.py /usr/local/pgmon/lib/
COPY main.py.src /tmp/main.py.src
RUN cd /tmp && sed "s|#{PYTHON_PATH}|#!/usr/bin/python3|" main.py.src | sed "s|#{APP_LIB_PATH}|/usr/local/pgmon/lib|" > main.py && rm main.py.src && mv main.py /usr/local/bin/pgmon && chmod +x /usr/local/bin/pgmon

ENTRYPOINT ["/usr/local/bin/pgmon", "-f"]
CMD ["-c", "/usr/local/pgmon/etc/pgmon.conf"]

FROM python:3.10-slim-buster as python-base

ENV POETRY_VERSION=1.4.2
ENV POETRY_HOME=/opt/poetry


FROM python-base as poetry-base

# Install Poetry
RUN python -m venv --system-site-packages $POETRY_HOME \
    && $POETRY_HOME/bin/pip install poetry==${POETRY_VERSION}


FROM python-base as app

# Copy Poetry to app image
COPY --from=poetry-base ${POETRY_HOME} ${POETRY_HOME}
# Add Poetry to PATH
ENV PATH="${PATH}:${POETRY_HOME}/bin"

COPY . .
RUN poetry export --only main,app --without-hashes -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["app.py"]

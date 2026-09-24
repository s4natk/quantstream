FROM python:3.12-slim AS build

WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

WORKDIR /app
COPY --from=build /install /usr/local
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "quantstream.api"]

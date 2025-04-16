FROM python:3.11-alpine

WORKDIR /app


# Install PostgreSQL client libraries and build dependencies
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "main.py"]


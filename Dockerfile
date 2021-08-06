FROM python:3.9-slim

COPY . /src
WORKDIR /src
RUN pip install -e .

CMD ["polycal"]

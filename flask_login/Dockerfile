FROM python:3.12-alpine
RUN apk add build-base linux-headers
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt 
EXPOSE 4000 
CMD ["gunicorn", "-w 4", "-b", "0.0.0.0:8080", "main:app"]

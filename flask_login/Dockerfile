FROM python:3.7-alpine
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt 
EXPOSE 4000 
CMD ["gunicorn", "-w 4", "-b", "0.0.0.0:8080", "main:app"]

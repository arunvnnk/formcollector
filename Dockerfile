FROM python:3.9

# Install dependencies
RUN pip install flask pymongo gunicorn bind

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 

COPY ./app/start.sh /bin/start.sh
RUN chmod +x /bin/start.sh
# Start application
CMD ["/bin/start.sh"]

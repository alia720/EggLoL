FROM python:3.11.4

WORKDIR /

COPY main /main/
COPY ./images/champion_icons /images/
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./main/main.py"]
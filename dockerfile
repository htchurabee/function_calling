FROM python:3.12
COPY ./src/app ./src/app/ 
COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt
WORKDIR /src/app
FROM joyzoursky/python-chromedriver:3.9

WORKDIR /src
COPY requirements.txt /src
RUN pip install -r requirements.txt

RUN mkdir -p saved_data

COPY . /src

CMD ["python", "parser.py"]
# # Используем официальный образ Python 3.12
# FROM python:3.12-slim

# # Устанавливаем необходимые пакеты
# # RUN apt-get update && apt-get install -y \
# #     wget \
# #     unzip \
# #     chromium \
# #     chromium-driver \
# #     && apt-get clean \
# #     && rm -rf /var/lib/apt/lists/*
# RUN apt-get install -y libglib2.0-0=2.50.3-2 \
#     libnss3=2:3.26.2-1.1+deb9u1 \
#     libgconf-2-4=3.2.6-4+b1 \
#     libfontconfig1=2.11.0-6.7+b1

# # Устанавливаем рабочую директорию
# WORKDIR /app

# # Копируем файл с зависимостями в контейнер
# COPY requirements.txt .

# # Устанавливаем зависимости
# RUN pip install --no-cache-dir -r requirements.txt

# # Копируем остальные файлы проекта в контейнер
# COPY . .

# # Запускаем скрипт parser.py
# CMD ["python", "parser.py"]



FROM joyzoursky/python-chromedriver:3.9

WORKDIR /src
COPY requirements.txt /src
RUN pip install -r requirements.txt

RUN mkdir -p saved_data

COPY . /src

CMD ["python", "parser.py"]
import json
from datetime import datetime
from time import sleep
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
)
from pprint import pprint

BASE_URL = "https://tenchat.ru"
URL = "https://tenchat.ru/media/3045210-nedavno-pobyval-na-zakrytoy-vstreche-s-oskarom-khartmanom"
URL2 = "https://tenchat.ru/media/3055500-kak-rossiyane-pokupayut-v-aptekakh-i-gde-uznayut-o-novykh-predlozheniyakh"
XPATH_BTN = "/html/body/div[1]/div/div[1]/div[2]/main/div/div[1]/div[1]/div/div/div/div[3]/div/div/div[2]/button"


def open_all_comments():
    url = URL
    driver: webdriver.Chrome = setup(url)
    driver.implicitly_wait(5)

    xpath_btn = XPATH_BTN

    count_iterations = 0  # TODO запихать в декоратор
    while True:
        count_iterations += 1
        if count_iterations > 10:
            break
        try:
            more_comments_button = driver.find_element(by=By.XPATH, value=xpath_btn)
        except NoSuchElementException:
            break

        try:
            # Попытка кликнуть на элемент
            more_comments_button.click()
        except ElementClickInterceptedException:
            # Если возникает исключение, используем JavaScript для клика
            driver.execute_script("arguments[0].click();", more_comments_button)

    page = driver.page_source
    teardown(driver)
    return page


def setup(url: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Запуск в безголовом режиме
    chrome_options.add_argument("--no-sandbox")  # Отключение песочницы
    chrome_options.add_argument("--disable-dev-shm-usage")  # Отключение использования /dev/shm
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    return driver


def teardown(driver):
    driver.quit()


def get_comments_data(previous_comment: str, last_comment_only: bool = False):
    page = open_all_comments()

    soup = BeautifulSoup(page, "lxml")

    comments_cls = "min-w-0 bg-white shadow-xxs mobile:shadow-none rounded-2xl p-5 pb-2 mobile:p-4 mobile:pb-1"
    comments_block = soup.find("div", class_=comments_cls)

    exact_comment_cls = "flex flex-col"
    comments = comments_block.find_all(
        "div", class_=exact_comment_cls, attrs={"data-cy": "comment"}
    )
    if last_comment_only:
        comments = [comments[-1]]

    all_comments_data = []
    for comment_block in comments:
        comment_content = comment_block.find("div", attrs={"data-cy": "content"}).text
        comment_content = strip_comment_ending(comment_content)
        if last_comment_only and previous_comment == comment_content:
            return False
        comment_creator = comment_block.find(
            "div", attrs={"data-cy": "comment-creator"}
        )
        link_to_comment_creator = (
            BASE_URL
            + comment_creator.find(
                "a", class_="tc-btn-focus flex flex-col items-center rounded-full"
            ).attrs["href"]
        )
        commentator_name, commentator_photo_url = get_commentator_profile(
            link_to_comment_creator
        )
        comment_mapping = {
            "name": commentator_name,
            "text": comment_content,
            "photo_url": commentator_photo_url,
        }
        all_comments_data.append(comment_mapping)

    return all_comments_data


def strip_comment_ending(text: str) -> str:
    return text.removesuffix("Развернуть")


def get_commentator_profile(profile_link: str):
    response = requests.get(profile_link)
    html = response.text
    soup = BeautifulSoup(html, "lxml")
    name = soup.find("h1", attrs={"data-cy": "name"}).text
    photo_source = soup.find("script", type="application/ld+json")
    contents = photo_source.contents[0]
    photo_url = json.loads(contents)["image"]["url"]
    return name, photo_url


def download_photo(url, now_time: datetime):
    response = requests.get(url)
    if response.status_code == 200:
        # Открываем файл в бинарном режиме и записываем содержимое
        with open(f"saved_data/Фото_комментатора_{now_time}.jpg", "wb") as file:
            file.write(response.content)
    else:
        print("Не удалось скачать изображение. Статус код:", response.status_code)


def save_comment(comment_data: dict, now_time: datetime):
    with open(f"saved_data/Комментарий_{now_time}.md", mode="a") as file:
        file.write(f"**{comment_data['name']}**\n\n\n")
        file.write(f"{comment_data['text']}\n\n\n")
        file.write(f"{comment_data['photo_url']}")


def main():
    previous_comment_text = ""

    input_prompt = (
        "Выберите две цифры (1 или 2). 1 - если нужно собрать "
        "данные по всем комментариям поста; 2 - если только по последнему: "
    )
    input_warning = "Допустим ввод только цифр 1 или 2!"
    user_input = input(input_prompt)
    if user_input not in ["1", "2"]:
        return input_warning
    if user_input == "1":
        comments_data = get_comments_data(previous_comment_text)
    else:
        input_prompt = "Задайте частоту в минутах, с которой скрипт будет проверять наличие нового комментария: "
        wrong_delay_type = "Задержка задается только с помощью целых чисел!"
        try:
            delay_input = int(input(input_prompt))
        except ValueError:
            return wrong_delay_type
        while True:
            now = datetime.now().replace(microsecond=0)
            comments_data = get_comments_data(previous_comment_text, last_comment_only=True)
            if not comments_data:
                print("Не обнаружено новых комментариев")
                print(f"Ожидаю {delay_input} минут до следующей проверки...\n\n")
                sleep(delay_input*60)
                continue
            else:
                previous_comment_text = comments_data[0]["text"]
                download_photo(comments_data[0]["photo_url"], now)
                print(f"\n##### НОВЫЙ КОММЕНТАРИЙ #####\n{comments_data}\n")
                save_comment(comments_data[0], now)
            print(f"Ожидаю {delay_input} минут до следующей проверки...\n\n")
            sleep(delay_input*60)
    return comments_data if user_input == "1" else "_|_Работа скрипта прервана_|_"


if __name__ == "__main__":
    pprint(main())

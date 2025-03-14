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
    StaleElementReferenceException,
)
from pprint import pprint

BASE_URL = "https://tenchat.ru"
URL = "https://tenchat.ru/media/3045210-nedavno-pobyval-na-zakrytoy-vstreche-s-oskarom-khartmanom"
XPATH_BTN = "/html/body/div[1]/div/div[1]/div[2]/main/div/div[1]/div[1]/div/div/div/div[3]/div/div/div[2]/button"


class WebDriverManager:
    def __init__(self):
        self.driver = self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def teardown(self):
        self.driver.quit()


class Comment:
    def __init__(self, name, text, photo_url):
        self.name = name
        self.text = text
        self.photo_url = photo_url

    def to_dict(self):
        return {
            "name": self.name,
            "text": self.text,
            "photo_url": self.photo_url,
        }


class CommentParser:
    def __init__(self, driver_manager):
        self.driver_manager = driver_manager

    def open_all_comments(self, url):
        driver = self.driver_manager.driver
        driver.get(url)
        driver.implicitly_wait(5)

        count_iterations = 0
        while True:
            count_iterations += 1
            if count_iterations > 10:
                break
            try:
                more_comments_button = driver.find_element(by=By.XPATH, value=XPATH_BTN)
            except NoSuchElementException:
                break

            try:
                more_comments_button.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", more_comments_button)
            except StaleElementReferenceException:
                continue

        return driver.page_source

    def get_comments_data(self, page_source, previous_comment=None, last_comment_only=False):
        soup = BeautifulSoup(page_source, "lxml")
        comments_cls = "min-w-0 bg-white shadow-xxs mobile:shadow-none rounded-2xl p-5 pb-2 mobile:p-4 mobile:pb-1"
        comments_block = soup.find("div", class_=comments_cls)

        exact_comment_cls = "flex flex-col"
        comments = comments_block.find_all("div", class_=exact_comment_cls, attrs={"data-cy": "comment"})

        if last_comment_only:
            comments = [comments[-1]]

        all_comments_data = []
        for comment_block in comments:
            comment_content = comment_block.find("div", attrs={"data-cy": "content"}).text
            comment_content = self.strip_comment_ending(comment_content)
            if last_comment_only and previous_comment == comment_content:
                return False

            comment_creator = comment_block.find("div", attrs={"data-cy": "comment-creator"})
            link_to_comment_creator = BASE_URL + comment_creator.find(
                "a", class_="tc-btn-focus flex flex-col items-center rounded-full"
            ).attrs["href"]
            commentator_name, commentator_photo_url = self.get_commentator_profile(link_to_comment_creator)

            comment = Comment(commentator_name, comment_content, commentator_photo_url)
            all_comments_data.append(comment.to_dict())

        return all_comments_data

    def strip_comment_ending(self, text):
        return text.removesuffix("Развернуть")

    def get_commentator_profile(self, profile_link):
        response = requests.get(profile_link)
        html = response.text
        soup = BeautifulSoup(html, "lxml")
        name = soup.find("h1", attrs={"data-cy": "name"}).text
        photo_source = soup.find("script", type="application/ld+json")
        contents = photo_source.contents[0]
        photo_url = json.loads(contents)["image"]["url"]
        return name, photo_url


class CommentDownloader:
    @staticmethod
    def download_photo(url, now_time):
        response = requests.get(url)
        if response.status_code == 200:
            with open(f"saved_data/Фото_комментатора_{now_time}.jpg", "wb") as file:
                file.write(response.content)
        else:
            print("Не удалось скачать изображение. Статус код:", response.status_code)

    @staticmethod
    def save_comment(comment_data, now_time):
        with open(f"saved_data/Комментарий_{now_time}.md", mode="a") as file:
            file.write(f"**{comment_data['name']}**\n\n\n")
            file.write(f"{comment_data['text']}\n\n\n")
            file.write(f"{comment_data['photo_url']}")


class TenChatScraper:
    def __init__(self):
        self.driver_manager = WebDriverManager()
        self.comment_parser = CommentParser(self.driver_manager)
        self.comment_downloader = CommentDownloader()

    def main(self):
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
            page_source = self.comment_parser.open_all_comments(URL)
            comments_data = self.comment_parser.get_comments_data(page_source)
        else:
            input_prompt = "Задайте частоту в минутах, с которой скрипт будет проверять наличие нового комментария: "
            wrong_delay_type = "Задержка задается только с помощью целых чисел!"
            try:
                delay_input = int(input(input_prompt))
            except ValueError:
                return wrong_delay_type

            while True:
                now = datetime.now().replace(microsecond=0)
                page_source = self.comment_parser.open_all_comments(URL)
                comments_data = self.comment_parser.get_comments_data(page_source, previous_comment_text,
                                                                      last_comment_only=True)
                if not comments_data:
                    print("Не обнаружено новых комментариев")
                    print(f"Ожидаю {delay_input} минут до следующей проверки...\n\n")
                    sleep(delay_input * 60)
                    continue
                else:
                    previous_comment_text = comments_data[0]["text"]
                    self.comment_downloader.download_photo(comments_data[0]["photo_url"], now)
                    print(f"\n##### НОВЫЙ КОММЕНТАРИЙ #####\n{comments_data}\n")
                    self.comment_downloader.save_comment(comments_data[0], now)
                print(f"Ожидаю {delay_input} минут до следующей проверки...\n\n")
                sleep(delay_input * 60)

        return comments_data if user_input == "1" else "_|_Работа скрипта прервана_|_"


if __name__ == "__main__":
    scraper = TenChatScraper()
    pprint(scraper.main())

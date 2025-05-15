import concurrent.futures
import re
import time
import random
from aiohttp import BasicAuth
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import LOGGER
from typing import List
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import asyncio
from readability import Document
from data_processing import remove_unwanted_tags, replace_img_tags, clean_html_tags, remove_html_attributes
from utils import get_status_description, load_config, get_proxy
from config_chrome_options import chrome_options
from gsearch_parser import GSearch_Selenium_Parser_alt
from playsound import playsound
import traceback
from logging.handlers import RotatingFileHandler
# Ліміт для кількості одночасних екземплярів браузера
MAX_BROWSER_INSTANCES = 2
browser_semaphore = asyncio.Semaphore(MAX_BROWSER_INSTANCES)

# Глобальний лічильник для порядку парсингу
parsing_counter = 0

import logging

# Створюємо обробник для файлу
file_handler = RotatingFileHandler("parser.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)  # Увімкнути DEBUG логи для запису у файл
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

# Створюємо обробник для консолі
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # У консолі будуть лише INFO і вище
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

# Очищаємо існуючі обробники
for handler in logging.getLogger().handlers[:]:
    logging.getLogger().removeHandler(handler)

# Додавання обробників (унікальних)
if not logging.getLogger().handlers:
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(console_handler)

# Встановлюємо загальний рівень логера
logging.getLogger().setLevel(logging.DEBUG)

# Фільтруємо зайві логи від зовнішніх бібліотек
logging.getLogger("webdriver_manager").setLevel(logging.CRITICAL)  # Вимикаємо всі логи, окрім CRITICAL
logging.getLogger("WDM").setLevel(logging.CRITICAL)  # Додаємо обмеження для WDM
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.CRITICAL)
LOGGER.setLevel(logging.CRITICAL)  # Вимикає логи WebDriver
logging.getLogger("selenium").setLevel(logging.CRITICAL)  # Вимикаємо всі логи Selenium# Вимикаємо логи WebDriver
logging.getLogger("gpu").setLevel(logging.ERROR)

# Обмежуємо рівень логів для сторонніх бібліотек
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("readability").setLevel(logging.WARNING)  # Додаємо фільтрацію для "readability" Не показувати в лог файлі логи з реабіліту.
logging.getLogger("multipart.multipart").setLevel(logging.WARNING)  # Вимикаємо DEBUG для multipart
logging.getLogger("asyncio").setLevel(logging.WARNING)  # Вимикаємо DEBUG для asyncio

status_description = 'Помилка при обробці'
# Завантаження конфігурації
config = load_config('config.yaml')

# async def Https_Parser(url: str) -> str:
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#     }
#     proxy = get_proxy()
#     try:
#         timeout_time = config.get('timeout_time', 15)
#         timeout = aiohttp.ClientTimeout(total=timeout_time)
#
#         async with aiohttp.ClientSession(timeout=timeout) as session:
#             async with session.get(url, headers=headers, proxy=proxy) as response:
#                 status_code = response.status
#                 global status_description
#                 status_description = get_status_description(response.status)
#                 logging.info(status_description)
#                 if status_code == 200:
#                     response_text = await response.text()
#                     return response_text
#                 else:
#                     logging.error(f"Помилка: не вдалося отримати доступ до сторінки {url} (Статус-код: {status_code})")
#                     return ''
#     except Exception as e:
#         logging.error(f"Помилка при обробці URL {url}: {str(e)}")
#         return ''

async def Https_Parser(url: str) -> str:
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority': 'u=0, i',
        # 'referer': 'https://www.eldorado.ru/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'upgrade-insecure-requests': '1',
        # 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'user-agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/118.0.5993.70 Safari/537.36'
    }
    proxy = get_proxy()
    retry_count = 0
    max_retries = 5
    if not hasattr(Https_Parser, 'total_processed'):
        Https_Parser.total_processed = 0
    if not hasattr(Https_Parser, 'total_urls'):
        Https_Parser.total_urls = 0

    use_delays = config.get('random_delay', False)

    while retry_count < max_retries:
        print(f"\n{'=' * 100}")
        print(f"[HTTPS][СПРОБА {retry_count + 1}/{max_retries}] {url}")

        if use_delays:
            random_delay = random.uniform(2, 5)
            print(f"[HTTPS] Очікування {random_delay:.1f}с...")
            await asyncio.sleep(random_delay)

        try:
            timeout_time = config.get('timeout_time', 15)
            timeout = aiohttp.ClientTimeout(total=timeout_time)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    status_code = response.status
                    global status_description
                    status_description = get_status_description(response.status)
                    if status_code in [429, 403, 503, 502, 500]:
                        if use_delays:
                            wait_time = random.uniform(5, 15)
                            print(f"[HTTPS] Помилка {status_code}, очікування {wait_time:.1f}с")
                            logging.warning(f"Код {status_code} для {url}")
                            await asyncio.sleep(wait_time)
                        retry_count += 1
                        continue
                    if status_code == 200:
                        Https_Parser.total_processed += 1
                        print(f"[HTTPS] Успішно | Оброблено {Https_Parser.total_processed}/{Https_Parser.total_urls}")
                        print(f"{'=' * 100}")
                        return await response.text()
                    print(f"[HTTPS] Помилка {status_code}")
                    retry_count += 1
                    if use_delays:
                        await asyncio.sleep(random.uniform(3, 7))
        except (asyncio.TimeoutError, Exception) as e:
            print(f"[HTTPS] Помилка: {str(e)}")
            retry_count += 1
            if use_delays:
                await asyncio.sleep(random.uniform(3, 7))

    print(f"[HTTPS] Вичерпано всі спроби для {url}")
    print(f"{'=' * 100}")
    return ''


async def process_urls_batch(urls: List[str]):
    total_sites = len(urls)
    Https_Parser.total_urls = len(urls)
    Https_Parser.total_processed = 0

    for i in range(0, len(urls), 3):
        remaining_sites = total_sites - Https_Parser.total_processed
        batch = urls[i:i + 3]
        tasks = [Https_Parser(url) for url in batch]
        await asyncio.gather(*tasks)
        if i + 3 < len(urls):
            await asyncio.sleep(1)

# ПАРСИНГ САЙТІВ СЕЛЕНІУМОМ
def Selenium_Parser(url: str, driver=None) -> str:
    """
    Функція для парсингу статей за допомогою Selenium.
    Додано детальні логи, обробку помилок і перевірку статусу.

    Args:
        url (str): URL сторінки для парсингу.
        driver (webdriver.Chrome, optional): Інстанс браузера. Якщо None, створюється новий.

    Returns:
        str: HTML-код сторінки або пустий рядок у разі помилки.
    """
    if not driver:
        # Отримуємо базові опції з config_chrome_options
        options = chrome_options()
        # Вимкнення завантаження зображень
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        # Встановлюємо рівень логування Selenium на ERROR
        LOGGER.setLevel(logging.ERROR)
        options.add_argument("--headless") # Додаємо тільки для цієї функції режим headless. Відключаємо загрузку вікна хром.
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install(), log_path="nul"),  # Вимикає логи WebDriver
            options=options
        )

    # Налаштування Selenium Stealth
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    global parsing_counter
    parsing_counter += 1
    logging.info(f"[ЕТАП 1: СТАРТ ПАРСИНГУ] #{parsing_counter} - Selenium почав парсинг сторінки: {url}")
    logging.debug(f"[DEBUG] Елемент <body> знайдено на сторінці: {url}")    #print(f"Selenium відкрив {url}")

    try:
        # Завантаження сторінки
        import requests

        def is_site_available(url):
            try:
                response = requests.head(url, timeout=5)
                return response.status_code == 200
            except requests.RequestException:
                return False

        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        # Очікуємо, поки сторінка повністю завантажиться
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info(f"[ЕТАП 2: Selenium] Сторінка повністю завантажена: {url}")

        # Прокрутка сторінки з очікуванням появи конкретного елемента
        scroll_duration = 15  # Тривалість прокрутки в секундах
        scroll_speed = 300  # Швидкість прокрутки, скролінг (в пікселях за один крок) Було 180 в старому коді.

        start_time = time.time()
        while time.time() - start_time < scroll_duration:
            driver.execute_script(f"window.scrollBy(0, {scroll_speed});")
            time.sleep(random.uniform(0.5, 1))  # Інтервал між прокрутками
        logging.debug(f"[Selenium_Parser] Прокрутка сторінки виконана: {url}")

        # Отримуємо HTML-код сторінки
        page_source = driver.page_source

        # Логування успішного парсингу
        logging.info(f"[ЕТАП 3:] Парсинг сторінки завершено: {url}")
        return page_source

    except Exception as e:
        # Обробляємо виключення під час завантаження сторінки
        if isinstance(e, Exception):
            logging.critical(f"[ERROR] Парсинг сторінки {url} завершився з помилкою: {e.msg if hasattr(e, 'msg') else str(e)}")
        else:
            logging.error(f"[Selenium_Parser] Невідома помилка для {url}: {str(e)}")
        logging.debug(f"Деталі помилки: {traceback.format_exc()}")
        return ''


    finally:
        try:
            driver.quit()
            logging.debug(f"[Selenium_Parser] Драйвер закрито для {url}")
        except Exception as e:
            logging.error(f"[Selenium_Parser] Помилка при закритті драйвера: {str(e)}")



def process_url_with_selenium(url: str, driver = None) -> str:
    try:
        return Selenium_Parser(url, driver=driver)
    except Exception as e:
        logging.error(f'Exception occurred in Selenium processing: {e}')
        return ''

async def extract_content(url: str,
                          ignore_list: List[str],
                          ignore_words: List[str],
                          ignore_sentence: List[str],
                          code_v: str='0',
                          parser_type='https',
                          driver=None):
    if parser_type == 'https':
        page_source = await Https_Parser(url)
    elif parser_type == 'Selenium':
        page_source = GSearch_Selenium_Parser_alt(url, driver=driver)
    elif parser_type == 'Selenium-old':
        page_source = process_url_with_selenium(url, driver=driver)
    else:
        logging.error(f'Невірний тип парсера: {parser_type}')
        page_source = ''
    return await analysis_html(url, page_source, code_v, ignore_list, ignore_words, ignore_sentence)



async def analysis_html(url: str, page_source: str, code_v: str, break_list: List[str], ignore_words: List[str], ignore_sentence: List[str]) -> dict:
    if page_source == '':
        logging.error(f'Неможливо обробити порожній контент для URL: {url}')
        return {
            'Status Parsing': 'НІ',
            'ID': '1.2.',
            'Title': 'No Title',
            'Content': BeautifulSoup('<p>None</p>', 'html.parser'),
            'URL': url,
            'Код відповіді': status_description,
            'Image Url_original': '',
            'Image now Url': ''
        }
    try:
        soup = BeautifulSoup(page_source, 'html.parser')
        title_tag = soup.find('h1')
        title_html = title_tag.prettify() if title_tag else '<h1></h1>'
        title_text = title_tag.get_text(strip=True) if title_tag else 'No Title'

        # Проходимо по всіх зображеннях у HTML
        for img in soup.find_all('img'):
            # Перевіряємо, чи є атрибут 'src' у зображення
            if img.get('src', ""):
                src = img['src']
                # Перевіряємо, чи є джерело зображення відносним посиланням
                if src.startswith('/'):  # Перевірка, чи є джерело зображення відносним посиланням
                    # Додаємо хост базової URL-адреси до джерела зображення
                    img['src'] = f"{urlparse(url).scheme}://{urlparse(url).hostname}{src}"
                if src.startswith("data:"):
                    img.decompose()

        content = []
        if code_v == '0':
            content = parse_readability(soup, break_list, ignore_words, ignore_sentence)
            content_html = f'{title_html}{"".join(content)}'
        elif code_v == '1':
            if title_tag:
                # Знайти всі елементи після h1
                content = parse_after_h1_remove_after_stopword(soup, break_list, ignore_words, ignore_sentence)
                content_html = f'{title_html}{content}'
        elif code_v == '2':
            if title_tag:
                # Обходимо всі наступні елементи на тому ж рівні вкладеності дей h1
                content = parse_sibling_elements_after_h1(title_tag, break_list, ignore_words, ignore_sentence)
                content_html = f'{title_html}{"".join(content)}'

        content_html = BeautifulSoup(content_html, 'html.parser')
        # Очищення та обробка HTML контенту

        content_html = clean_html_tags(content_html)
        content_html = remove_unwanted_tags(content_html)
        content_html = remove_html_attributes(content_html)

        images = content_html.find_all('img')
        image_urls_original = [urljoin(url, img.get('src')) for img in images if img.get('src')]

        images = content_html.find_all('img')
        content_html = replace_img_tags(content_html, url)
        image_urls = [urljoin(url, img.get('src')) for img in images if img.get('src')]
        return {
            'Status Parsing': 'ТАК',
            'ID': '1.2.',
            'Title': title_text,
            'Content': content_html,
            'URL': url,
            'Код відповіді': status_description,
            'Image Url_original': ' \n'.join(image_urls_original),
            'Image now Url': ' \n'.join(image_urls)
        }
    except Exception as e:
        logging.error(f"Помилка при обробці URL {url}: {str(e)}")
        return {
            'Status Parsing': 'НІ',
            'ID': '1.2.',
            'Title': 'No Title',
            'Content': BeautifulSoup('<p>None</p>', 'html.parser'),
            'URL': url,
            'Код відповіді': status_description,
            'Image Url_original': '',
            'Image now Url': ''
        }



def ignore_sentences_filter(ignore_sentence, html):
    for sentence in ignore_sentence:
        ignore_sentence_pattern = re.escape(sentence)
        # Видаляємо всі блоки, що містять ці речення
        html = re.sub(
            rf'<[^>]*>\s*.*?\b{ignore_sentence_pattern}\b.*?</[^>]*>',
            '',
            html,
            flags=re.IGNORECASE
        )
    return html
def ignore_words_filter(ignore_words, html):
    for word in ignore_words:
        ignore_word_pattern = re.escape(word)
        html = re.sub(rf'\b{ignore_word_pattern}\b', '', html, flags=re.IGNORECASE)
    return html
def break_list_filter(break_list, html):
    for phrase in break_list:
        stopword_pattern = re.escape(phrase)
        html = re.sub(rf'>*{stopword_pattern}.*', '', html, flags=re.DOTALL)
        # Шукаємо перший закриваючий тег '>'
        closing_tag_match = re.search(r'<[^>]*>[^<]*$', html, re.DOTALL)
        if closing_tag_match:
            closing_tag_index = closing_tag_match.start()
            # Обрізаємо текст після першого закриваючого тега
            html = html[:closing_tag_index]
    return html

def parse_sibling_elements_after_h1(title_tag: BeautifulSoup, break_list: List[str], ignore_words: List[str], ignore_sentence: List[str]) -> str:
    """
    Обробляє всі наступні сусідні елементи після тега <h1> на тому ж рівні вкладеності.

    :param title_tag: Тег <h1> після якого потрібно обробити сусідні елементи.
    :param break_list: Список слів для зупинки обробки.
    :param ignore_words: Список слів для ігнорування в тексті.
    :param ignore_sentence: Список речень для ігнорування.
    :return: Відредагований HTML-контент.
    """
    if not title_tag:
        return ""
    html = title_tag.find_next_siblings()
    html = ''.join([str(tag) for tag in html])
    after_h1_content = ''
    # Видаляємо речення, які містять слова з ignore_sentence
    html = ignore_sentences_filter(ignore_sentence, html)
    # ігнорує вказане слово з списку ignore_words
    html = ignore_words_filter(ignore_words, html)
    # Видалити все після першого стоп-слова
    html = break_list_filter(break_list, html)

    return html
def parse_after_h1_remove_after_stopword(html: BeautifulSoup, break_list: List[str], ignore_words, ignore_sentence) -> str:
    """
    Обробляє HTML-контент, знаходячи тег <h1>, забираючи все після нього,
    а також видаляючи контент після стоп-слова.

    :param html: Весь HTML-контент як один рядок.
    :param break_list: Список стоп-слів.
    :return: Відредагований HTML-контент.
    """
    # Знаходимо перший блок <h1> і все, що йде після нього
    h1_pattern = r'(<h1[^>]*>.*?</h1>)(.*)'
    match = re.search(h1_pattern, str(html), re.DOTALL)

    if match:
        # Все, що йде після <h1>
        html = match.group(2)

        # Видаляємо речення, які містять слова з ignore_sentence
        html = ignore_sentences_filter(ignore_sentence, html)
        # ігнорує вказане слово з списку ignore_words
        html = ignore_words_filter(ignore_words, html)
        # Видалити все після першого стоп-слова
        html = break_list_filter(break_list, html)

    return html


def parse_readability(html: BeautifulSoup, break_list: List[str], ignore_words: List[str], ignore_sentence: List[str]) -> str:
    """
    Парсить HTML-код за допомогою readability для отримання очищеного тексту та інтегрує зображення.

    :param html: HTML-код статті як об'єкт BeautifulSoup.
    :param break_list: Список стоп слів, якщо є таке слово, то далі нічого не зберігаємо.
    :param ignore_words: Список слів для ігнорування в тексті.
    :param ignore_sentence: Список речень для ігнорування.
    :return: Відредагований HTML-контент.
    """

    html_text = str(html)
    # Використовуємо readability для отримання очищеного HTML
    doc = Document(html_text)
    article_html = doc.summary()  # Очищена розмітка тексту

    # Використовуємо BeautifulSoup для парсингу очищеного HTML
    soup = BeautifulSoup(article_html, 'html.parser')

    # Знаходимо всі зображення в оригінальному HTML
    original_soup = BeautifulSoup(html_text, 'html.parser')
    images = original_soup.find_all('img')

    # Зберігаємо зображення у словник для швидкого доступу
    img_dict = {img['src']: str(img) for img in images}

    # Обробляємо очищений HTML, замінюючи зображення за їх `src`
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if src in img_dict:
            img_tag.replace_with(BeautifulSoup(img_dict[src], 'html.parser'))

    # Форматування очищеного HTML
    cleaned_html = str(soup)

    # Видаляємо речення, які містять слова з ignore_sentence
    cleaned_html = ignore_sentences_filter(ignore_sentence, cleaned_html)
    # Ігнорує вказане слово з списку ignore_words
    cleaned_html = ignore_words_filter(ignore_words, cleaned_html)
    # Видалити все після першого стоп-слова
    cleaned_html = break_list_filter(break_list, cleaned_html)

    return cleaned_html

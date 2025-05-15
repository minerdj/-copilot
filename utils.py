"""
Цей модуль містить утиліти для роботи з конфігураційними файлами, HTTP статусами,
перетворенням HTML в XML та створенням ZIP архівів.

Функції:
1. `load_config(config_file)`: Завантажує конфігурацію з YAML файлу.
   - Параметри:
     - `config_file` (str): Шлях до YAML файлу конфігурації.
   - Повертає:
     - dict: Словник з конфігураційними налаштуваннями.
   - Викидає:
     - FileNotFoundError: Якщо файл не знайдено.

2. `get_status_description(status_code)`: Повертає опис статус-коду HTTP.
   - Параметри:
     - `status_code` (int): Код HTTP статусу.
   - Повертає:
     - str: Опис статусу у форматі "Код відповіді: <код> - <опис>".

3. `html_to_xml(html_content)`: Перетворює HTML в XML формат.
   - Параметри:
     - `html_content` (BeautifulSoup): HTML контент у вигляді BeautifulSoup об'єкта.
   - Повертає:
     - str: XML представлення HTML контенту.

4. `create_zip_archive(files, zip_file_path)`: Створює ZIP архів з файлів.
   - Параметри:
     - `files` (list): Список шляхів до файлів, які потрібно включити в архів.
     - `zip_file_path` (str): Шлях до створюваного ZIP архіву.
   - Викидає:
     - FileNotFoundError: Якщо якийсь з файлів не знайдено.

"""
import json
import aiohttp
import asyncio
import logging
import html2text
import yaml
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urljoin, unquote, urlparse
import os
from googlesearch import search, _req, SearchResult
from googlesearch.user_agents import get_useragent
import requests
from functools import cache

import urllib3
from urllib.parse import urlparse

urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
import time
import random
from bs4 import BeautifulSoup
from playsound import playsound
from gsearch_parser import GSearch_Selenium_Parser_alt # process_gsearch_url_with_selenium

logging.basicConfig(level=logging.INFO, filename='parser.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')



logging.getLogger("seleniumwire").setLevel(logging.CRITICAL)
#-----------------------------------------------------------

# сайт для провірки проксі. Як що проксі не пройшов перевірку. МОЖЛИВО НЕ ПРАЦЮЄ САЙТ https://ya.ru


#@cache
def get_proxy():
    if not 1: # ВИМКНУТИ ПРОКСІ ЯКИЙ ПАРСИТЬ САЙТИ НА РЕКВЕСТАХ. 1 - юзати проксі, 0 - не юзати
        return
    config = load_config("config.yaml")
    PROXY_CHECK_URL = config.get("proxy_check_url", "https://ya.ru/")
    if not config.get("proxy_config", []):
        return
    proxy_list = config.get('proxy_config', [])
    if not isinstance(proxy_list, list):
        proxy_list = [proxy_list]

    while proxy_list:
        proxy = random.choice(proxy_list)
        p_url = urlparse(proxy)
        try:
            proxies = {
                "http": proxy,
                "https": proxy
            }
            if p_url.scheme in ["socks5", "socks6"]:
                proxies = { p_url.scheme: proxy }

            r = requests.get(PROXY_CHECK_URL, proxies=proxies)
            r.raise_for_status()
            print(f"Використано проксі-сервер({proxy}): {r.text[:50]}")
            return proxy
        except Exception as e:
            print("Проксі не пройшов перевірку ", proxy, e)
            proxy_list.remove(proxy)
    print(f"Усі проксі не пройшли перевірку\n МОЖЛИВО НЕ ПРАЦЮЄ САЙТ {PROXY_CHECK_URL}")


def load_config(config_file: str):
    """Завантажує конфігурацію з YAML файлу."""
    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Файл конфігурації {config_file} не знайдено.")
    with open(config_file, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def blacklist(blacklist_file: str):
    """blacklist - список сторінок які потрібно блокувати txt"""
    if not os.path.isfile(blacklist_file):
        raise FileNotFoundError(f"Файл blacklist :  {blacklist_file} не знайдено.")
    with open(blacklist_file, 'r', encoding='utf-8') as file:
        return file.read().split('\n')


def add_unreachable_site(blacklist_file: str, site_url: str):
    print(blacklist_file)
    """
    Додає недоступний сайт у файл.

    blacklist_file - назва текстового файлу, в який записуються недоступні сайти.
    site_url - URL сайту, який потрібно додати до списку недоступних.
    """
    # Отримуємо шлях до поточної директорії
    current_directory = os.getcwd()

    # Створюємо повний шлях до файлу
    blacklist_file_path = os.path.join(current_directory, blacklist_file)
    print(blacklist_file_path)
    # Перевіряємо, чи файл існує і створюємо його, якщо необхідно
    file_exists = os.path.isfile(blacklist_file_path)

    if not file_exists:
        with open(blacklist_file_path, 'w', encoding='utf-8') as file:
            pass  # Просто створюємо порожній файл

    # Читаємо існуючі сайти, якщо файл існує
    existing_sites = set()
    if file_exists:
        with open(blacklist_file_path, 'r', encoding='utf-8') as file:
            existing_sites = set(file.read().splitlines())

    # Додаємо сайт у файл, якщо його ще немає
    if site_url not in existing_sites:
        with open(blacklist_file_path, 'a', encoding='utf-8') as file:
            file.write(site_url + '\n')
            logging.info(f"Сайт {site_url} додано до тимчасового списку недоступних.")
    else:
        logging.info(f"Сайт {site_url} вже є у тимчасовому списку недоступних.")


def get_status_description(status_code: int)->str:
    """Повертає опис статус-коду HTTP."""
    from http import HTTPStatus
    try:
        description = HTTPStatus(status_code).description
        return f"Код відповіді: {status_code} - {description}"
    except ValueError:
        return f"Невідомий код відповіді: {status_code}"


def html_to_xml(html_content: BeautifulSoup):
    """
    Перетворює HTML-контент у формат XML.
    Якщо виникає помилка або результат порожній, зберігає HTML-контент як XML.

    :param html_content: Об'єкт BeautifulSoup, що містить HTML-контент.
    :return: XML-контент у вигляді рядка.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.Element("root")

        def parse_element(element, parent):
            tag = ET.SubElement(parent, element.name)
            for attr, value in element.attrs.items():
                tag.set(attr, value)
            if element.string:
                tag.text = element.string.strip()
            for child in element.children:
                if isinstance(child, str):
                    continue
                parse_element(child, tag)

        parse_element(html_content, root)
        xml_result = ET.tostring(root, encoding='unicode')

        if not xml_result.strip():
            raise ValueError("Результат перетворення пустий.")

    except Exception as e:
        # Якщо виникає помилка, зберігаємо HTML-контент як XML
        xml_result = f"<root><![CDATA[{html_content}]]></root>"
    return xml_result


def create_zip_archive(files: list, zip_file_path: str):
    """Створює ZIP архів з файлів."""
    print('Створює ZIP архів з файлів')
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for file in files:
            if os.path.isfile(file):
                zipf.write(file, os.path.basename(file))
            else:
                raise FileNotFoundError(f"Файл {file} не знайдено.")



def search_with_recommend_block_alt(term, num_results=10, lang="en", proxy=None, sleep_interval=0,
                                timeout=5, safe="active", ssl_verify=None, region=None, driver=None,
                                  proxy_list: list = None, proxy_chrome = None):
    """Search the Google search engine"""

    # Proxy setup
    # proxies = {"https": proxy, "http": proxy} if proxy and (
    #             proxy.startswith("https") or proxy.startswith("http")) else None

    start = 0
    fetched_results = 0  # Keep track of the total fetched results

    while fetched_results < num_results:
        # params_url = f"https://www.google.com/search?q={term}&num={num_results - start + 2}&hl={lang}&start={start}&safe={safe}&gl={region}"
        page_source = GSearch_Selenium_Parser_alt(term, driver, bool(start))
        if not page_source:
            print("[ERROR] Can not solve captcha from google or other error (no page source (alt))")
            # input("Dlya prodovjennia natysnit enter") # нужно тільки для дебагу помилок всяких
            return

        if page_source == "restart":

            start = 0
            fetched_results = 0
            print("Trying to restart pagination")
            continue

        with open("google_resp2_solved.html", "w", encoding="utf-8") as f:
            f.write(page_source)

        soup = BeautifulSoup(page_source, "html.parser")

        for x in (soup.find_all(attrs={"jsname": "yEVEwb"}) or []):
            markdown_text = html2text.html2text(str(x))
            title = markdown_text.split("(")[0].replace("[", "").replace("]", "").replace("**", "").replace("\n", " ").strip()
            print(f"Find similar title '{title}'")
            yield SearchResult("", title, "")

        result_block = soup.find_all("div", attrs={"class": "MjjYud"})
        new_results = 0  # Keep track of new results in this iteration

        for result in result_block:
            # Find link, title, description
            link = result.find("a", href=True)
            title = result.find("h3")
            description_box = result.find("div", {"style": "-webkit-line-clamp:2"})

            if link and title and description_box:
                description = description_box.text
                fetched_results += 1
                new_results += 1
                yield SearchResult(link["href"], title.text, description)

            if fetched_results >= num_results:
                return  # Stop if we have fetched the desired number of results

        if new_results == 0:
            # If you want to have printed to your screen that the desired amount of queries can not been fulfilled, uncomment the line below:
            # print(f"Only {fetched_results} results found for query requiring {num_results} results. Moving on to the next query.")
            break  # Break the loop if no new results were found in this iteration

        # ПАУЗА МІЖ СТОРІНКАМИ ПАГІНАЦІЇ В ГУГЛ ПОШУКУ
        start += 10  # Prepare for the next set of results
        time.sleep(sleep_interval)


def get_google_search_results_alt(query: str, num_results: int = 10, need_titles: bool = False, driver=None):
    """
    Отримує перші `num_results` посилань з Google за запитом `query`.

    :param query: Пошуковий запит
    :param num_results: Кількість результатів для отримання
    :return: Список URL-адрес
    """

    max_attempts = 5  # Кількість спроб, взяти результати з гугл пошука, як що капча.
    attempt = 0  # Лічильник спроб
    config = load_config('config.yaml')
    lang = config.get('lang', '')
    region = config.get('region', '')
    safe = config.get('safe', "off")

    urls = []


    while attempt < max_attempts:
        try:
            if need_titles:
                for search_result in search_with_recommend_block_alt(query,
                                                                     num_results=num_results,
                                                                     lang=lang,
                                                                     region=region,
                                                                     safe=safe,
                                                                     sleep_interval=int(random.uniform(1, 3)), # Рандомна пауза була: (а:5, b:15)
                                                                     driver=driver):
                    urls.append(search_result.title)

            else:
                for search_result in search_with_recommend_block_alt(query,
                                                                     num_results=num_results,
                                                                     lang=lang,
                                                                     region=region,
                                                                     safe=safe,
                                                                     sleep_interval=int(random.uniform(1, 3)), # Рандомна пауза була: (а:5, b:15)
                                                                     driver=driver):
                    if search_result.url:
                        urls.append(search_result.url)

        except Exception as e:
            print(f"Виникла помилка: {e}")

            if "429" in str(e):
                print("Затримка через помилку 429...")
                playsound(r'./audio/kapcha_long_version.mp3')
                attempt += 1
                time.sleep(random.uniform(5, 30))  # Затримка перед повторною спробою
            continue

        if urls:
            print(f'ОК тема : \t {query}')
            break  # Якщо список URL-адрес не порожній, виходимо з циклу
        else:
            attempt += 1  # Збільшуємо лічильник спроб і повторюємо
            print(f'Google нічого не вернув, повторно робимо запит №{attempt} на тему :\t\t{query}')

    if not urls:
        print(f"Після {max_attempts} спроб результати не знайдено.")

    if need_titles:
        list(set(urls))

    return list(set(urls))[:num_results]


def download_images(image_urls, download_folder):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    list_image_path = []

    for i, url in enumerate(image_urls):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Перевірка на помилки

            # Отримання імені файлу з URL
            parsed_url = urlparse(url)
            file_name = os.path.basename(unquote(parsed_url.path))
            file_path = os.path.join(download_folder, file_name)

            with open(file_path, 'wb') as file:
                file.write(response.content)

            list_image_path.append(file_path)
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            logging.info(f"Помилка: URL '{url[:15]}' не є вірним або сталася інша помилка під час завантаження.")

    return list_image_path


def gen_rand_text(text_len: int = None):
    alph = list("abcdefghijklmnopqrstuvwxyz")
    random.shuffle(alph)
    return "".join(alph[:(text_len or 5)])
claimed_names = []

#Скачування картинок основна функція
# -------------------------------------------------------
# Скачування Selenium Ware при помилках 503, 403
#Скачування картинок основна функція
# -------------------------------------------------------
# Скачування Selenium при помилках 503, 403
def selenium_download_image(proxy_url, file_url, download_folder):
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium_stealth import stealth
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from urllib.parse import urlparse, unquote
    import os
    import time
    import random
    import json
    import socket

    def create_proxy_extension(proxy_url):
        """Створення manifest.json і background.js для авторизації проксі."""
        print(f"[DEBUG] Аналіз проксі: {proxy_url}")
        proxy_auth = proxy_url.split("@")
        if len(proxy_auth) != 2:
            raise ValueError("Некоректний формат проксі: очікується 'логін:пароль@адреса_проксі'")

        auth_part = proxy_auth[0]
        address_part = proxy_auth[1]

        if ":" not in auth_part:
            raise ValueError("Некоректний формат авторизації в проксі: очікується 'логін:пароль'")
        try:
            username, password = auth_part.split(":", 1)  # Використовуємо maxsplit=1, щоб уникнути помилок
        except ValueError as e:
            raise ValueError(f"Помилка розділення логіна і пароля в проксі '{proxy_url}': {e}")
        proxy_address = address_part

        # Структура manifest.json
        manifest = {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Proxy Authentication",
            "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>"],
            "background": {
                "scripts": ["background.js"]
            }
        }

        # Логіка у background.js
        background_js = f"""
        chrome.webRequest.onAuthRequired.addListener(
            function handler(details) {{
                return {{authCredentials: {{username: "{username}", password: "{password}"}}}};
            }},
            {{urls: ["<all_urls>"]}},
            ['blocking']
        );
        """

        # Створення директорії для розширення
        extension_path = "extension"
        os.makedirs(extension_path, exist_ok=True)
        with open(f"{extension_path}/manifest.json", "w") as manifest_file:
            json.dump(manifest, manifest_file, indent=4)
        with open(f"{extension_path}/background.js", "w") as background_file:
            background_file.write(background_js)
        print(f"[DEBUG] Розширення для проксі створено: {extension_path}")

        return extension_path

    try:
        host = "rg-21933.sp5.ovh"
        ip = socket.gethostbyname(host)
        print(f"[DEBUG] DNS резолвінг успішний: {host} -> {ip}")
    except socket.gaierror as e:
        print(f"[DEBUG] Помилка резолвінгу DNS для {host}: {e}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu") # Закоментувати щоб включити загрузку Selenium (Візуалізація)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    chrome_options.add_argument("--disable-software-rasterizer")
    print(proxy_url)

    # Альтернативний підхід: додаємо проксі безпосередньо
    chrome_options.add_argument("--proxy-server=http://CmaxKK0gH_0:BhcIyGZAuFYd@rg-21933.sp5.ovh:11001")

    # ЩОБ ВИКЛЮЧИТИ PROXY SELENIUM ЗАКОМЕНТУВАТИ: if proxy_url і chrome_options.add_argument (ctrl + /)
    # Інтеграція з розширенням для проксі
    if proxy_url:
        extension_path = create_proxy_extension(proxy_url)
        chrome_options.add_argument(f"--load-extension={extension_path}")

    # Ініціалізація драйвера без Selenium Wire
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    # Використання selenium-stealth для антідетекту
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)

    try:
        # Перевірка IP через проксі
        driver.get("https://api.ipify.org")
        current_ip = driver.find_element(By.TAG_NAME, "body").text
        print('IP через проксі: ', current_ip)

        # Завантаження зображення
        driver.get(file_url)
        time.sleep(random.uniform(2, 8))

        if "captcha" in driver.page_source.lower():
            input(f"Обнаружена капча! Решите её и нажмите Enter для продолжения...")

        img_element = driver.find_element(By.TAG_NAME, "img")

        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        # Отримання імені файлу
        parsed_url = urlparse(file_url)
        original_filename = os.path.basename(unquote(parsed_url.path))
        if not original_filename:
            original_filename = f"downloaded_{int(time.time())}.png"
        else:
            name, ext = os.path.splitext(original_filename)
            original_filename = f"{name}{ext}"

        save_path = os.path.join(download_folder, original_filename)

        # Збереження зображення
        img_element.screenshot(save_path)
        print(f"Изображение сохранено в {save_path}")
        return True

    except Exception as e:
        print(f"Ошибка: {e}")
        return False
    finally:
        driver.quit()

# Получаем ip через aiohttp
async def fetch_ip(proxy=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org", proxy=proxy) as response:
                ip = await response.text()
                return ip
    except Exception as e:
        print(f"[aiohttp] Ошибка при получении IP: {e}")
        return None

# -------------------------------------------------------
#  Скачування картинок реквестами
async def download_images_v2(image_urls, download_folder, session = None):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority': 'u=0, i',
        #'referer': 'https://www.eldorado.ru/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'upgrade-insecure-requests': '1',
        #'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'user-agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/118.0.5993.70 Safari/537.36'
    }

    # Заміна URL як що силка редеріктить.
    #image_urls = [url.replace("https://www.eldorado.ru", "https://static.eldorado.ru") for url in image_urls]

    proxy = None

    list_image_path = []
    if not isinstance(image_urls, list):
        image_urls = [image_urls]
    #proxy = get_proxy()
    # old code
    """
    retry_count = 0
    max_retries = 5
    retry_sleep = 3
    between_urls_sleep = 3
    for i, url in enumerate(image_urls):
        while retry_count < max_retries:
            retry_count += 1
            try:
                response = session.get(url, headers=headers, verify=False)
                # if response.status_code in [429, 403, 503, 502, 500]:
                #     # use selenium
                #     from parser import Selenium_Parser # local import to avoid circle imports
                #     selenium_result = Selenium_Parser(url)

                response.raise_for_status()  # Перевірка на помилки

                # Отримання імені файлу з URL
                parsed_url = urlparse(url)
                file_name = os.path.basename(unquote(parsed_url.path))
                name, file_format = file_name.rsplit(".", 1)
                while True:
                    new_file_name = gen_rand_text() + "." + file_format
                    if new_file_name in claimed_names:
                        continue
                    claimed_names.append(new_file_name)
                    # file_path = os.path.join(download_folder, new_file_name) # file_name
                    file_path = download_folder + "/" + new_file_name # file_name
                    break

                with open(file_path, 'wb') as file:
                    file.write(response.content)

                list_image_path.append(file_path)
            except Exception as e:
                print(f"Error downloading {url}: {e}")
                logging.info(f"Помилка: URL '{url[:15]}' не є вірним або сталася інша помилка під час завантаження.")
                if retry_count < max_retries:
                    await asyncio.sleep(retry_sleep)
        await asyncio.sleep(between_urls_sleep)
    """

    errorDownload = 0

    for i, url in enumerate(image_urls):
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            # закоментувати proxy = get_proxy() щоб виключити проксі саме в цій функції скачування реквестами
            proxy = get_proxy()
            config = load_config("config.yaml")

            print(f"\n{'=' * 100}")
            print(f"[HTTPS][СПРОБА {retry_count + 1}/{max_retries}] {url}")

            random_delay = random.uniform(2, 5)
            print(f"[HTTPS] Очікування {random_delay:.1f}с...")
            await asyncio.sleep(random_delay)

            try:
                timeout_time = 15
                timeout = aiohttp.ClientTimeout(total=timeout_time)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers, proxy=proxy) as response:
                        status_code = response.status

                        ip_address = await fetch_ip(proxy)
                        if ip_address:
                            print("Текущий IP (aiohttp):", ip_address)
                        else:
                            print("Не удалось получить IP через aiohttp.")

                        global status_description
                        status_description = get_status_description(response.status)
                        if status_code in [429, 502, 500]:
                            wait_time = random.uniform(5, 15)
                            print(f"[HTTPS] Помилка {status_code}, очікування {wait_time:.1f}с")
                            logging.warning(f"Код {status_code} для {url}")
                            await asyncio.sleep(wait_time)
                            retry_count += 1
                            continue
                        # Додати код помилки: Щоб селеніум качав.
                        if status_code in [403, 503, 500]:
                            print(f"[HTTPS] Помилка {status_code} --> Selenium")
                            # ЩОБ ВИКЛЮЧИТИ PROXY SELENIUM ЗАКОМЕНТУВАТИ: config, proxys, print, proxy (ctrl + /)
                            selenium_proxys = config.get('proxy_config_selenium', [])
                            selenium_proxy = random.choice(selenium_proxys)
                            print(f"[Selenium] Використовується проксі: {selenium_proxy}")
                            statusS = selenium_download_image(selenium_proxy, url, download_folder)

                            if statusS:
                                parsed_url = urlparse(url)
                                file_name = os.path.basename(unquote(parsed_url.path))
                                try:
                                    name, file_format = file_name.rsplit(".", 1)
                                except ValueError:
                                    # Если расширение не удалось определить, задаём стандартное
                                    file_format = "jpg"
                                new_file_name = gen_rand_text() + "." + file_format
                                file_path = os.path.join(download_folder, file_name)
                                new_file_path = os.path.join(download_folder, new_file_name)

                                if os.path.exists(file_path):
                                    os.rename(file_path, new_file_path)
                                    list_image_path.append(new_file_path)
                                    print(f"[Selenium] Успішно")
                                else:
                                    errorDownload += 1
                                    print(f"[Selenium] Error")
                            break

                        if status_code == 200:
                            print(f"[HTTPS] Успішно")
                            print(f"{'=' * 100}")
                            # Отримання імені файлу з URL
                            parsed_url = urlparse(url)
                            file_name = os.path.basename(unquote(parsed_url.path))
                            name, file_format = file_name.rsplit(".", 1)
                            while True:
                                new_file_name = gen_rand_text() + "." + file_format
                                if new_file_name in claimed_names:
                                    continue
                                claimed_names.append(new_file_name)
                                # file_path = os.path.join(download_folder, new_file_name) # file_name
                                file_path = download_folder + "/" + new_file_name  # file_name
                                break

                            with open(file_path, "wb") as f:
                                f.write(await response.read())

                            list_image_path.append(file_path)
                            print(f"[INFO] Додано новий файл до списку: {file_path}")
                            break
                        else:
                            print(f"[HTTPS] Помилка {status_code}")
                            retry_count += 1
                            if retry_count == 6:
                                errorDownload += 1
                            await asyncio.sleep(random.uniform(3, 7))
            except (asyncio.TimeoutError, Exception) as e:
                print(f"[HTTPS] Помилка: {str(e)}")
                retry_count += 1
                await asyncio.sleep(random.uniform(3, 7))

    print("LIST:", list_image_path)

    return list_image_path, len(list_image_path), errorDownload


import sys
import json
import logging
import random
import time
import traceback
import urllib.parse

import requests
from itertools import filterfalse

from playsound import playsound
from selenium import webdriver
from selenium_stealth import stealth # from local history
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import yaml

from config_chrome_options import chrome_options

logging.basicConfig(level=logging.INFO, filename='parser.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)


# старий код, зараз виключений
"""
def GSearch_Selenium_Parser(url: str) -> str:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options())
    try:
        driver.get(url)
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        cnt = 0
        while True:
            cnt += 1
            page_source = driver.page_source
            if "Our systems have detected unusual traffic from your computer network" in page_source:
                # Captcha is not solved yet
                # print(f"Captcha is not solved yet ({cnt} seconds)")
                time.sleep(1)
                continue

            break

        all_cookies = driver.get_cookies()
        cookies_dict = {}
        for cookie in all_cookies:
            cookies_dict[cookie['name']] = cookie['value']
        # print(cookies_dict)
        with open("google_search_cookies.json", "w", encoding="utf-8") as f:
            json.dump(cookies_dict, f, ensure_ascii=False, indent=4)

        # time.sleep(1)
        # page_source = driver.page_source
    except Exception as e:
        logging.error(f'Помилка у Selenium: {str(e)}')
        page_source = ''
    finally:
        try:
            driver.close()
            driver.quit()
        except Exception as e:
            logging.error(f'Помилка при закритті драйвера Selenium: {str(e)}')
            page_source = ''
    return page_source


def process_gsearch_url_with_selenium(url: str) -> str:
    try:
        return GSearch_Selenium_Parser(url)
    except Exception as e:
        logging.error(f'Exception occurred in Selenium processing gsearch link: {e}')
        return ''
"""


def GSearch_Selenium_Parser_alt(q: str, driver: webdriver.Chrome, paginate_next: bool = False) -> str:
    driver_wait = WebDriverWait(
        driver,
        timeout=3,
        poll_frequency=0.5,
        ignored_exceptions=[
            NoSuchElementException
        ]
    )

    # from local history
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)

    try:
        if paginate_next:
            print("Continue paginate...")
            # el = driver.find_element(By.ID, "pnnext")
            if not "google.com" in driver.current_url:
                driver.back()
                time.sleep(10)

            el = driver_wait.until(
                lambda d: d.find_element(By.ID, "pnnext"),
                message="Not found pagination next link"
            )

            if not el:
                return ''

            buttons = driver.find_elements(By.XPATH, '//*[@id="L2AGLb"]')

            for btn in buttons:
                btn.click()
                time.sleep(10)
            # print(el)

            el.click()
            time.sleep(1)
        else:
            print("Start paginate...")
            curr_tab = driver.current_window_handle
            next_tab = str(random.randint(100000, 999999))
            driver.execute_script(f"window.open('about:blank','{next_tab}');")
            time.sleep(0.2)
            driver.switch_to.window(curr_tab)
            driver.close()
            driver.switch_to.window(f"{next_tab}")

            driver.get("https://google.com")

            buttons = driver.find_elements(By.XPATH, '//*[@id="L2AGLb"]')

            for btn in buttons:
                btn.click()
                time.sleep(10)

            search_textarea = driver_wait.until(
                lambda d: d.find_element(By.CSS_SELECTOR, "textarea"),
                message="Not found search input"
            )
            for x in q:  # Швидкість друку букв: Дуже швидкий:  Швидкий: 0.01, 0.09, Плавний друк 0.1, 0.3. Змінювати в 2 строках.
                search_textarea.send_keys(x)
                time.sleep(random.uniform(0.01, 0.09))

            time.sleep(random.uniform(0.01, 0.09))
            search_textarea.send_keys(Keys.ENTER)

        # ПАУЗА чекати на сторінці гугл пошуку SELENIUM
        # driver.get(url)
        driver_wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(random.uniform(3, 6))  # чекати на сторінці пошуку. Було (5, 15)

        can_force_req = False
        cnt = 0
        while True:
            cnt += 1
            page_source = driver.page_source

            # Код для решения капчи: использование сервиса 2captcha.
            def solve_google_captcha(driver, sitekey, data_s, captcha_url):
                for attempt in range(config['captcha_attempts']):
                    print(f"[CAPTCHA] Спроба {attempt + 1} з {config['captcha_attempts']}")
                    cookie_string = ';'.join([f"{c['name']}:{c['value']}" for c in driver.get_cookies()])
                    data = {
                        'key': config['twocaptcha_api_key'],
                        'method': 'userrecaptcha',
                        'googlekey': sitekey,
                        'pageurl': captcha_url,
                        'data-s': data_s,
                        'cookies': cookie_string,
                        'json': 1
                    }

                    print("[CAPTCHA] Надсилання запиту до сервісу 2captcha...")
                    response = requests.post('https://2captcha.com/in.php', data=data)
                    print(f"[CAPTCHA] Відповідь від сервісу: {response.text}")
                    result = response.json()

                    if result['status'] == 1:
                        captcha_id = result['request']
                        for i in range(24):
                            time.sleep(5)
                            response = requests.get(
                                f'https://2captcha.com/res.php?key={config["twocaptcha_api_key"]}&action=get&id={captcha_id}&json=1')
                            print(f"[CAPTCHA] Очікування результату: {response.text}")
                            result = response.json()

                            if result['status'] == 1:
                                code = result['request']
                                print(f"[CAPTCHA] Отримано код рішення: {code}")
                                recaptcha_response = driver.find_element(By.ID, "g-recaptcha-response")
                                driver.execute_script(f'arguments[0].innerHTML = "{code}";', recaptcha_response)
                                print("[CAPTCHA] Встановлено рішення від 2captcha")

                                q_param = captcha_url.split('q=')[1].split('&')[0] if 'q=' in captcha_url else ''
                                continue_param = captcha_url.split('continue=')[1].split('&')[
                                    0] if 'continue=' in captcha_url else ''
                                submit_url = f"https://www.google.com/sorry/index?q={q_param}&continue={continue_param}&g-recaptcha-response={code}"

                                can_force_req = True
                                driver.get(submit_url)
                                print("[CAPTCHA] Відправлено рішення")
                                return True

                    print(f"[CAPTCHA] Спроба {attempt + 1} не вдалася")
                    if attempt == config['captcha_attempts'] - 1:
                        print("[CAPTCHA] Всі спроби автоматичного рішення вичерпано. Очікування ручного введення...")
                        playsound(r'./audio/kapcha_long_version.mp3')
                        start_time = time.time()
                        while time.time() - start_time < config['manual_solve_time']:
                            if driver.find_elements(By.CSS_SELECTOR, "#search span > a"):
                                print("[CAPTCHA] Капчу успішно вирішено вручну")
                                return True
                            time.sleep(5)
                return False
            # Обработка ошибки, вызов сервиса для решения капчи, получение данных для отправки к API
            if (
                "Captcha could not be solved" in page_source or
                "Our systems have detected unusual traffic from your computer network" in page_source or
                "CAPTCHA" in page_source
            ):
                print(f"[CAPTCHA] Виявлено захист від ботів на {driver.current_url}")
                while True:
                    sitekey = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
                    data_s = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-s")
                    captcha_url = driver.current_url

                    t = urllib.parse.urlparse(captcha_url)
                    t_param = urllib.parse.parse_qs(t.query)
                    continue_url = t_param["continue"]#[0]

                    print(f"[CAPTCHA] Знайдено ключ reCAPTCHA: {sitekey}")
                    print(f"[CAPTCHA] Знайдено data-s: {data_s}")
                    print(f"[CAPTCHA] URL: {captcha_url}")
                    print(f"[CAPTCHA] URL TO CONTINUE: {continue_url}")

                    if solve_google_captcha(driver, sitekey, data_s, captcha_url):
                        # while not driver.find_elements(By.CSS_SELECTOR, "#search span > a"):
                        time.sleep(5)
                        print("[CAPTCHA] Капчу успішно пройдено")
                        driver.get(continue_url)
                        break
                continue
            if can_force_req:
                 # Проблема з капчою. Бот зупинивься. Print (Відправлено рішення) Гугл не переадресував обратно на сторінку гугл пошуку.
                 # пауза коли капчу пройшли і пробуємо загуглити заново і в новій вкладці.
                # допомагає продовжити роботу боту після капчі
                time.sleep(3)
                driver_wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                return "restart"

            if "Your client does not have permission to get URL" in page_source:
                # driver.delete_all_cookies()
                # driver.refresh()
                print(f"Get permission error when fetching site ({cnt} attempts)")
                time.sleep(1)
                continue


            break

        elements = driver_wait.until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#search span > a"),
            message="Not found search results"
        )
        page_source = driver.page_source
        if random.random() < (1 / 10):  # Шанс відкрити сторінку з пошуку (1/10 одну з пяти)
            if elements:
                # перейти на один із результатів пошуку
                random_element = random.choice(elements)
                random_element.click()
            # затримка на сторінці(з пошуку яку відкрив) # Була а:5 - b:15
            time.sleep(random.uniform(5, 10))

    except Exception as e:
        # print(f'Помилка у Selenium: {str(e)}')
        print('Помилка у Selenium: ' + "".join(traceback.format_exception(*sys.exc_info())))
        logging.error(f'Помилка у Selenium: {str(e)}')
        page_source = ''
    finally:
        pass

    return page_source

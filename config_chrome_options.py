from selenium.webdriver.chrome.options import Options
from pathlib import Path
import os
import urllib.request
import zipfile


data_dir = Path(os.getcwd()) / "chrome_data"
data_dir.mkdir(parents=True, exist_ok=True)


def chrome_options():
    # Налаштування ChromeOptions
    chrome_options = Options()

    # Запуск браузера в прихованому режимі
    # chrome_options.add_argument("--headless")  # Прихований режим
    chrome_options.add_argument("--disable-gpu")  # Вимкнути апаратне прискорення
    chrome_options.add_argument("--no-sandbox")  # Вимкнути пісочницю
    # Додаємо рівень логування для Chrome
    chrome_options.add_argument("--log-level=3")  # Встановлює рівень логів на FATAL
    chrome_options.add_argument("--disable-dev-shm-usage")  # Вимкнути спільне використання пам'яті
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Антідетект бота. Сховати заголовок автоматизації. WebDriver. Допоміг з гуглом.

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # chrome_options.add_argument("--disable-extensions")  # Вимкнути розширення
    # chrome_options.add_argument("--disable-popup-blocking")  # Вимкнути блокування спливаючих вікон
    chrome_options.add_argument(f"--user-data-dir={data_dir}") # данні з браузера зберігати в data_dir (Chrome data)
    #
    # user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    # chrome_options.add_argument(f"user-agent={user_agent}")

    # chrome_options.add_argument(f"--user-data-dir={data_dir}")  # данні з браузера зберігати в data_dir


    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    # FIXME: like circular import
    from utils import get_proxy
    # Налаштування проксі для селеніуму (Якщо є )
    # просто так не вийде треба або через лібу або через wire
    # if proxy := get_proxy():
    #     chrome_options.add_argument(f'--proxy-server={proxy}')

    return chrome_options

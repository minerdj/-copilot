"""
Цей модуль реалізує функції для обробки HTML-контенту та збереження даних.

## Імпортовані бібліотеки

- `logging`, `re`, `random`, `os`: стандартні бібліотеки Python.
- `pandas`: для обробки даних.
- `BeautifulSoup`: для роботи з HTML.
- `FastAPI`: для обробки HTTP відповідей.
- `utils`: для допоміжних функцій.

## Налаштування

- **Логування**: Логи зберігаються у файлі `parser.log`.
- **Конфігурація**: Завантажується з `config.yaml`.

## Функції

- **`save_parsed_data(data)`**: Зберігає парсингові дані в DataFrame.
- **`convert_data_to_files(parsed_data, filetype)`**: Конвертує дані в формат `xlsx`, `csv`, або `xml` і повертає шлях до файлу.
- **`remove_unwanted_tags(html_content)`**: Видаляє небажані теги і стилі з HTML-контенту.
- **`clean_html_tags(soup)`**: Видаляє конкретні теги з HTML-контенту.
- **`should_ignore(text, ignore_list)`**: Перевіряє, чи текст містить стоп-слова.
- **`replace_img_tags(content_html, base_url)`**: Замінює теги `<img>` на абсолютні URL.
- **`remove_html_attributes(html_content)`**: Видаляє вказані атрибути з HTML-контенту.
- **`extract_content_after_h1(soup)`**: Витягує контент після першого `<h1>` до стопових слів.


"""

import logging
import re
from typing import List
from urllib.parse import urljoin
import pandas as pd
import random
import os
from bs4 import BeautifulSoup
from utils import html_to_xml, create_zip_archive, load_config, download_images
from fastapi.responses import HTMLResponse, FileResponse

logging.basicConfig(level=logging.INFO, filename='parser.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

config = load_config('config.yaml')


def save_parsed_data(data):
    """Зберігає результати парсингу в DataFrame."""
    return pd.DataFrame([data])


async def convert_data_to_files(parsed_data: pd.DataFrame, filetype: str):
    """Конвертує дані в потрібний формат і повертає шлях до файлу."""
    files = []
    try:
        file_name_prefix = f'static/parsed_content_{random.randint(1000, 9999)}'

        if filetype == "xlsx":
            file_path = f'{file_name_prefix}.xlsx'
            # Збереження даних у форматі Excel за допомогою openpyxl через pandas
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                parsed_data.to_excel(writer, index=False)
            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            files.append(file_path)

        elif filetype == "csv":
            file_path = f'{file_name_prefix}.csv'
            parsed_data.to_csv(file_path, index=False)
            media_type = 'text/csv'
            files.append(file_path)

        elif filetype == "jpg":
            site_archives = []

            for _, row in parsed_data.iterrows():
                title = row['Title']
                image_url_series = row['Image Url_original']
                image_url_list = image_url_series.split(' ')  # Якщо URL у рядку розділені пробілом

                # Безпечна назва для директорії та архіву
                safe_title = re.sub(r'[\/\\:*?"<>|]', '_', title)
                download_folder = f'static/{safe_title}_{random.randint(1000, 9999)}'

                # Завантаження зображень
                list_image_path = download_images(image_url_list, download_folder)

                # Створення ZIP архіву для кожної статті
                site_zip_file_path = f'static/{safe_title}.zip'
                create_zip_archive(files=list_image_path, zip_file_path=site_zip_file_path)

                site_archives.append(site_zip_file_path)
            # Створення головного ZIP архіву, що містить всі архіви сайтів
            main_zip_file_path = f'{file_name_prefix}_all_sites.zip'
            create_zip_archive(files=site_archives, zip_file_path=main_zip_file_path)

            media_type = 'application/zip'
            files.append(main_zip_file_path)


        elif filetype == "xml":
            for _, row in parsed_data.iterrows():
                title = row['Title']
                content = row['Content']
                safe_title = re.sub(r'[\/\\:*?"<>|]', '_', title)
                file_name = f'static/{safe_title}_{random.randint(1000, 9999)}.xml'
                xml_data = html_to_xml(content)
                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write(xml_data)
                files.append(file_name)

            media_type = 'application/zip'
            zip_file_path = f'{file_name_prefix}.zip'
            create_zip_archive(files, zip_file_path)
            logging.info(f"Created ZIP archive at: {zip_file_path}")
            return zip_file_path, media_type

        else:
            return HTMLResponse(content="<h1>Unsupported file type</h1>", status_code=400)

        logging.info(f"Generated file: {files[0]} with media type: {media_type}")
        return files[0], media_type

    except Exception as e:
        logging.error(f"Error generating file: {e}")
        return HTMLResponse(content=f"<h1>Error generating file: {e}</h1>", status_code=500)


def remove_unwanted_tags(html_content: BeautifulSoup) -> BeautifulSoup:
    """Видаляє небажані теги і стилі з HTML-контенту, залишаючи вміст."""
    tags_to_remove = config.get('tags_to_remove', [])

    # Видалити небажані теги
    for tag in html_content.find_all(tags_to_remove):
        tag.unwrap()  # Видаляє тег, залишаючи його вміст

    # Видалити стильові атрибути
    if config.get('remove_style_attributes', False):
        for tag in html_content.find_all(True):  # True означає будь-який тег
            if 'style' in tag.attrs:
                del tag.attrs['style']

    return html_content


def clean_html_tags(soup: BeautifulSoup) -> BeautifulSoup:
    """Видаляє небажані теги з HTML-контенту."""
    tags_to_del = config.get('tags_to_del', [])
    for tag_name in tags_to_del:
        for unwanted in soup.find_all(tag_name):
            unwanted.decompose()
    return soup


def should_ignore(text: str, ignore_list: List[str]) -> bool:
    """Перевіряє, чи текст містить будь-яке з стоп-слова."""
    sentences = re.split(r'[.!?]', text)
    for sentence in sentences:
        for phrase in ignore_list:
            if phrase.lower() in sentence.lower():
                print(f"Stopping because phrase '{phrase}' found in sentence: '{sentence.strip()}'")
                return True
    return False


def replace_img_tags(content_html: BeautifulSoup, base_url: str) -> BeautifulSoup:
    img_tags_list = config.get('image_src_attributes', [])
    now_base__url_image = config.get('now_base_url_image', '')

    for img_tag in content_html.find_all('img'):
        for attr in img_tags_list:
            src = img_tag.get(attr)
            if now_base__url_image == '':
                if src:
                    absolute_url = urljoin(base_url, src)
                    img_tag[attr] = absolute_url

                srcset = img_tag.get('srcset')
                if srcset:
                    srcset = re.sub(r'https?://[^\s]+', lambda m: urljoin(base_url, m.group(0)), srcset)
                    img_tag['srcset'] = srcset
            else:
                if src:
                    # Отримуємо тільки назву файлу із шляху
                    filename = os.path.basename(src)
                    # Створюємо новий абсолютний URL з новим base_url і назвою файлу
                    absolute_url = urljoin(now_base__url_image, filename)
                    img_tag[attr] = absolute_url
                srcset = img_tag.get('srcset')
                if srcset:
                    srcset = re.sub(r'[^,\s]+', lambda m: urljoin(now_base__url_image, os.path.basename(m.group(0))), srcset)
                    img_tag['srcset'] = srcset

    return content_html
def _replace_img_tags(content_html: BeautifulSoup, base_url: str) -> BeautifulSoup:
    img_tags_list = config.get('image_src_attributes', [])

    # Отримуємо новий base_url, якщо він вказаний
    now_base__url_image = config.get('now_base__url_image', '')
    if now_base__url_image != '':
        base_url = now_base__url_image

    for img_tag in content_html.find_all('img'):
        for attr in img_tags_list:
            src = img_tag.get(attr)
            if src:
                # Отримуємо тільки назву файлу із шляху
                filename = os.path.basename(src)
                # Створюємо новий абсолютний URL з новим base_url і назвою файлу
                absolute_url = urljoin(base_url, filename)
                img_tag[attr] = absolute_url

        # Обробка srcset атрибута
        srcset = img_tag.get('srcset')
        if srcset:
            # Заміна всіх URL у srcset на новий base_url
            srcset = re.sub(r'[^,\s]+', lambda m: urljoin(base_url, os.path.basename(m.group(0))), srcset)
            img_tag['srcset'] = srcset

    return content_html

def remove_html_attributes(html_content: BeautifulSoup) -> BeautifulSoup:
    """Видаляє вказані атрибути з HTML-контенту."""
    attributes_to_remove = config.get('attributes_to_remove', [])
    for tag in html_content.find_all(True):  # True означає будь-який тег
        for attr in attributes_to_remove:
            if attr in tag.attrs:
                del tag.attrs[attr]

    return html_content


def extract_content_after_h1(soup: BeautifulSoup) -> BeautifulSoup:
    """Витягує контент після першого тегу <h1> до стопових слів."""
    first_h1 = soup.find('h1')
    stop_words = config.get('break_words', [])
    if not first_h1:
        raise ValueError("Tag <h1> not found.")

    elements_after_h1 = first_h1.find_all_next()
    html_content = ''.join(str(element) for element in elements_after_h1)

    if stop_words:
        stop_pattern = '|'.join(map(re.escape, stop_words))
        stop_match = re.search(stop_pattern, html_content, re.DOTALL)
        if stop_match:
            stop_index = stop_match.start()
            block_start = html_content.rfind('<', 0, stop_index)
            html_after_h1 = html_content[:block_start] if block_start != -1 else html_content[:stop_index]
        else:
            html_after_h1 = html_content
    else:
        html_after_h1 = html_content

    return BeautifulSoup(html_after_h1, 'lxml')

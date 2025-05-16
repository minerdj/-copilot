import subprocess
import sys
import os
import shutil
from datetime import datetime, timedelta
import demo




def copy_files(source, destination):
    """Функція для копіювання файлів і папок."""
    if not os.path.exists(destination):
        os.makedirs(destination)

    try:
        if os.path.isdir(source):
            shutil.copytree(source, os.path.join(destination, os.path.basename(source)), dirs_exist_ok=True)
        elif os.path.isfile(source):
            shutil.copy2(source, destination)
        print(f"Успішно скопійовано з {source} до {destination}")
    except Exception as e:
        print(f"Помилка під час копіювання: {e}")

def data_build():
    """Функція для запиту часу демо-версії від користувача."""
    while True:
        data = input("\t\tВкажіть кількість годин від сьогоднішнього дня (1 - це 1-а година, 2 - це 2-і години, ...). Для виходу введіть 'q':\n")
        if data == 'q':
            sys.exit()
        try:
            data = int(data)
            if data <= 0:
                print("Ведіть додатне ціле число.")
            else:
                return data
        except ValueError:
            print("Введіть ціле натуральне число.")

def select_version():
    """Логіка вибору версії програми."""
    while True:
        version_program = input("""
        Введіть номер потрібної версії програми:
        1 - Демо версія програми на вказаний період від сьогоднішнього дня
        2 - Повна версія програми
        """)

        if version_program == '1':
            data = data_build()
            demo.update_time_demo(datetime.now() + timedelta(hours=data), DEMO_VERSION='True')
            return

        elif version_program == '2':
            demo.update_time_demo(datetime.now() + timedelta(hours=1000000), DEMO_VERSION='False')
            return

        else:
            print("Невірний вибір. Повторіть ввод.")

def run_command(command):
    """Виконує системну команду."""
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Команда '{command}' виконана успішно.")
    except subprocess.CalledProcessError as e:
        print(f"Помилка під час виконання команди: {e}")
        sys.exit(1)

def main():
    """Основна функція для запуску процесу збірки проекту."""
    try:
        # Логіка вибору версії програми
        select_version()

        # Встановлюємо залежності
        command_install = 'pip install -r requirements.txt'
        run_command(command_install)

        # Збірка проекту за допомогою PyInstaller
        command_build = 'pyinstaller myapp.spec'
        run_command(command_build)

        # Копіюємо файли до директорії 'dist/main'
        copy_files('templates', 'dist/main')
        copy_files('static', 'dist/main')
        copy_files('audio', 'dist/main')
        copy_files('blacklist.txt', 'dist/main')
        copy_files('Blacklist_Domen.txt', 'dist/main')
        copy_files('Blacklist_Page.txt', 'dist/main')
        copy_files('config.yaml', 'dist/main')
        copy_files('parser.log', 'dist/main')
        copy_files('readability', 'dist/main')
        copy_files('Images Obrizatu Niz', 'dist/main')
        copy_files('Images Obrizatu Verh', 'dist/main')
        copy_files('YNIKALIZACIY', 'dist/main')
        copy_files('YDALUTY KARTINKU', 'dist/main')
        copy_files('Cliker man', 'dist/main')
        # copy_files('chrome_data', 'dist/main')
        copy_files('ydalytu_kesh.txt', 'dist/main')
        print("Збірка проекту успішно завершена!")

    except Exception as e:
        print(f"Сталася помилка: {e}")

if __name__ == "__main__":
    main()

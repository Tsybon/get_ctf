#!/usr/bin/env python3
"""
CTF Writeups to PDF Converter (Playwright version with PDF merging)
Автоматично конвертує всі writeup'и з GitHub репозиторію в PDF файли
та об'єднує їх в один великий PDF
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile
import markdown
from PIL import Image
import base64
import io
import re
import asyncio
from playwright.async_api import async_playwright

try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    MERGE_AVAILABLE = True
except ImportError:
    MERGE_AVAILABLE = False


class CTFWriteupConverter:
    def __init__(self, repo_path, output_dir="pdf_writeups"):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.generated_pdfs = []  # Список згенерованих PDF файлів

    def find_challenge_folders(self):
        """Знаходить всі папки з задачами (які містять README.md)"""
        challenges = []

        # Перевіряємо чи передали шлях до конкретної категорії (наприклад forensics)
        if self.repo_path.name in ['forensics', 'crypto', 'web', 'pwn', 'reverse', 'misc', 'hardware']:
            # Це конкретна категорія, шукаємо задачі безпосередньо в ній
            category_name = self.repo_path.name
            for challenge_path in self.repo_path.iterdir():
                if challenge_path.is_dir() and not challenge_path.name.startswith('.'):
                    readme_path = challenge_path / "README.md"
                    if readme_path.exists():
                        challenges.append({
                            'category': category_name,
                            'name': challenge_path.name,
                            'path': challenge_path,
                            'readme': readme_path
                        })
        else:
            # Це кореневий репозиторій, шукаємо у всіх категоріях
            for category_path in self.repo_path.iterdir():
                if category_path.is_dir() and not category_path.name.startswith('.'):
                    # Перевіряємо чи є підпапки з задачами
                    for challenge_path in category_path.iterdir():
                        if challenge_path.is_dir():
                            readme_path = challenge_path / "README.md"
                            if readme_path.exists():
                                challenges.append({
                                    'category': category_path.name,
                                    'name': challenge_path.name,
                                    'path': challenge_path,
                                    'readme': readme_path
                                })

        return challenges

    def process_images_in_markdown(self, markdown_content, assets_dir):
        """Обробляє зображення в markdown, конвертує їх в base64"""
        if not assets_dir.exists():
            return markdown_content

        def replace_image(match):
            alt_text = match.group(1) if match.group(1) else ""
            img_path = match.group(2)

            print(f"🔍 Обробляю зображення: {img_path}")

            # Варіанти шляхів для пошуку зображення
            possible_paths = []

            # 1. Якщо це відносний шлях до assets
            if img_path.startswith('assets/') or img_path.startswith('./assets/'):
                img_name = img_path.split('/')[-1]
                possible_paths.append(assets_dir / img_name)

            # 2. Якщо це просто назва файлу (без папки)
            elif '/' not in img_path:
                possible_paths.append(assets_dir / img_path)

            # 3. Якщо це повний відносний шлях
            else:
                # Спробуємо взяти тільки назву файлу
                img_name = img_path.split('/')[-1]
                possible_paths.append(assets_dir / img_name)

                # Також спробуємо повний шлях відносно папки задачі
                challenge_path = assets_dir.parent
                possible_paths.append(challenge_path / img_path)

            # Шукаємо файл у всіх можливих місцях
            for full_img_path in possible_paths:
                if full_img_path.exists():
                    try:
                        print(f"✅ Знайдено зображення: {full_img_path}")

                        # Конвертуємо зображення в base64
                        with open(full_img_path, 'rb') as img_file:
                            img_data = img_file.read()

                        # Визначаємо MIME тип
                        ext = full_img_path.suffix.lower()
                        mime_types = {
                            '.png': 'image/png',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.gif': 'image/gif',
                            '.svg': 'image/svg+xml',
                            '.webp': 'image/webp'
                        }
                        mime_type = mime_types.get(ext, 'image/png')

                        # Створюємо base64 data URL
                        base64_data = base64.b64encode(img_data).decode('utf-8')
                        return f'![{alt_text}](data:{mime_type};base64,{base64_data})'

                    except Exception as e:
                        print(f"❌ Помилка обробки зображення {full_img_path}: {e}")
                        continue

            print(f"⚠️  Зображення не знайдено: {img_path}")
            return match.group(0)  # Повертаємо оригінальний текст якщо не знайшли

        # Знаходимо всі markdown зображення
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        processed_content = re.sub(img_pattern, replace_image, markdown_content)

        return processed_content

    def markdown_to_html(self, markdown_content):
        """Конвертує markdown в HTML з підтримкою синтаксису коду"""
        md = markdown.Markdown(extensions=[
            'codehilite',
            'fenced_code',
            'tables',
            'toc'
        ])

        html_content = md.convert(markdown_content)

        # Додаємо CSS стилі для гарного відображення
        css_styles = """
        <style>
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 14px;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 2em;
            margin-bottom: 1em;
            page-break-after: avoid;
        }

        h1 {
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            font-size: 28px;
        }

        h2 {
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
            font-size: 22px;
        }

        h3 {
            font-size: 18px;
        }

        code {
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            color: #e74c3c;
        }

        pre {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: 11px;
        }

        img {
            max-width: 100%;
            height: auto;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            page-break-inside: avoid;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            font-size: 12px;
        }

        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }

        blockquote {
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding-left: 1em;
            color: #7f8c8d;
        }

        .challenge-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            page-break-after: avoid;
        }

        .challenge-category {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        </style>
        """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>CTF Writeup</title>
            {css_styles}
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

    async def convert_to_pdf(self, challenge, browser):
        """Конвертує один writeup в PDF"""
        try:
            print(f"Обробляю: {challenge['category']} - {challenge['name']}")

            # Читаємо markdown файл
            with open(challenge['readme'], 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Додаємо заголовок з інформацією про задачу
            header = f"""# {challenge['name']}

**Категорія:** {challenge['category']}

---

"""
            markdown_content = header + markdown_content

            # Обробляємо зображення
            assets_dir = challenge['path'] / 'assets'
            processed_markdown = self.process_images_in_markdown(markdown_content, assets_dir)

            # Конвертуємо в HTML
            html_content = self.markdown_to_html(processed_markdown)

            # Створюємо PDF
            output_filename = f"{challenge['category']}_{challenge['name'].replace(' ', '_')}.pdf"
            output_path = self.output_dir / output_filename

            # Створюємо тимчасовий HTML файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name

            try:
                # Створюємо нову сторінку
                page = await browser.new_page()

                # Завантажуємо HTML
                await page.goto(f'file://{temp_html_path}')

                # Генеруємо PDF
                await page.pdf(
                    path=str(output_path),
                    format='A4',
                    margin={
                        'top': '2cm',
                        'right': '2cm',
                        'bottom': '2cm',
                        'left': '2cm'
                    },
                    print_background=True
                )

                await page.close()

            finally:
                # Видаляємо тимчасовий файл
                os.unlink(temp_html_path)

            print(f"✅ Створено: {output_path}")
            self.generated_pdfs.append(output_path)  # Додаємо до списку
            return True

        except Exception as e:
            print(f"❌ Помилка при обробці {challenge['name']}: {e}")
            return False

    async def create_index_pdf(self, challenges, browser):
        """Створює індексний PDF з переліком всіх задач"""
        index_content = """# CTF Writeups Collection

## Список задач

"""

        # Групуємо по категоріям
        categories = {}
        for challenge in challenges:
            category = challenge['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(challenge['name'])

        for category, names in sorted(categories.items()):
            index_content += f"\n### {category.upper()}\n\n"
            for name in sorted(names):
                index_content += f"- {name}\n"

        index_content += f"\n\n**Всього задач:** {len(challenges)}\n"
        index_content += f"**Категорій:** {len(categories)}\n\n"
        index_content += "---\n\n*Згенеровано автоматично*"

        # Конвертуємо в PDF
        html_content = self.markdown_to_html(index_content)
        output_path = self.output_dir / "_INDEX.pdf"

        # Створюємо тимчасовий HTML файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_html_path = f.name

        try:
            page = await browser.new_page()
            await page.goto(f'file://{temp_html_path}')
            await page.pdf(
                path=str(output_path),
                format='A4',
                margin={'top': '2cm', 'right': '2cm', 'bottom': '2cm', 'left': '2cm'},
                print_background=True
            )
            await page.close()
        finally:
            os.unlink(temp_html_path)

        print(f"📋 Створено індекс: {output_path}")
        self.generated_pdfs.append(output_path)  # Додаємо індекс до списку

    def create_separator_page(self, title, output_path):
        """Створює сторінку-роздільник між PDF файлами"""
        if not MERGE_AVAILABLE:
            return None

        try:
            c = canvas.Canvas(str(output_path), pagesize=A4)
            width, height = A4

            # Встановлюємо фон
            c.setFillColorRGB(0.2, 0.3, 0.5)  # Темно-синій фон
            c.rect(0, 0, width, height, fill=True)

            # Заголовок
            c.setFillColorRGB(1, 1, 1)  # Білий текст
            c.setFont("Helvetica-Bold", 24)
            text_width = c.stringWidth(title, "Helvetica-Bold", 24)
            c.drawString((width - text_width) / 2, height / 2, title)

            # Лінія під заголовком
            c.setStrokeColorRGB(1, 1, 1)
            c.setLineWidth(2)
            line_start = (width - text_width) / 2
            line_end = line_start + text_width
            c.line(line_start, height / 2 - 10, line_end, height / 2 - 10)

            c.save()
            return output_path
        except Exception as e:
            print(f"❌ Помилка створення сторінки-роздільника: {e}")
            return None

    def merge_pdfs(self):
        """Об'єднує всі PDF файли в один"""
        if not MERGE_AVAILABLE:
            print("⚠️  PyPDF2 та reportlab не встановлені. Встановіть їх для об'єднання PDF:")
            print("pip install PyPDF2 reportlab")
            return False

        if not self.generated_pdfs:
            print("❌ Немає PDF файлів для об'єднання")
            return False

        try:
            print("\n🔗 Починаю об'єднання PDF файлів...")

            writer = PdfWriter()
            merged_path = self.output_dir / "ALL_WRITEUPS_MERGED.pdf"

            # Сортуємо PDF файли (індекс спочатку, потім по алфавіту)
            sorted_pdfs = sorted(self.generated_pdfs, key=lambda x: (
                0 if x.name == "_INDEX.pdf" else 1,
                x.name
            ))

            for pdf_path in sorted_pdfs:
                if not pdf_path.exists():
                    continue

                try:
                    # Створюємо сторінку-роздільник
                    separator_name = pdf_path.stem.replace('_', ' ').title()
                    if pdf_path.name == "_INDEX.pdf":
                        separator_name = "📋 ІНДЕКС"
                    else:
                        separator_name = f"📄 {separator_name}"

                    temp_separator = self.output_dir / f"temp_separator_{pdf_path.stem}.pdf"
                    separator_path = self.create_separator_page(separator_name, temp_separator)

                    # Додаємо роздільник
                    if separator_path and separator_path.exists():
                        with open(separator_path, 'rb') as sep_file:
                            sep_reader = PdfReader(sep_file)
                            for page in sep_reader.pages:
                                writer.add_page(page)
                        os.unlink(separator_path)  # Видаляємо тимчасовий файл

                    # Додаємо основний PDF
                    with open(pdf_path, 'rb') as pdf_file:
                        reader = PdfReader(pdf_file)
                        for page_num, page in enumerate(reader.pages):
                            writer.add_page(page)

                    print(f"✅ Додано: {pdf_path.name}")

                except Exception as e:
                    print(f"⚠️  Помилка при додаванні {pdf_path.name}: {e}")
                    continue

            # Записуємо об'єднаний PDF
            with open(merged_path, 'wb') as output_file:
                writer.write(output_file)

            print(f"\n🎉 Успішно створено об'єднаний PDF: {merged_path}")
            print(f"📊 Загальна кількість сторінок: {len(writer.pages)}")
            return True

        except Exception as e:
            print(f"❌ Помилка при об'єднанні PDF: {e}")
            return False

    async def run(self):
        """Основна функція запуску"""
        print("🚀 Починаю конвертацію CTF writeups...")

        # Знаходимо всі задачі
        challenges = self.find_challenge_folders()

        if not challenges:
            print("❌ Не знайдено жодної задачі з README.md")
            return

        print(f"📁 Знайдено {len(challenges)} задач:")
        for challenge in challenges:
            print(f"  - {challenge['category']}/{challenge['name']}")

        print(f"\n📄 Результати будуть збережені в: {self.output_dir.absolute()}")

        # Запускаємо браузер
        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # Створюємо індекс
            await self.create_index_pdf(challenges, browser)

            # Конвертуємо кожну задачу
            success_count = 0
            for challenge in challenges:
                if await self.convert_to_pdf(challenge, browser):
                    success_count += 1

            await browser.close()

        print(f"\n✅ Завершено конвертацію! Успішно створено: {success_count}/{len(challenges)} задач")

        # Об'єднуємо PDF файли
        if self.generated_pdfs:
            self.merge_pdfs()

        print(f"\n📁 Всі файли збережено в: {self.output_dir.absolute()}")
        print(f"📋 Індивідуальні PDF: {len(self.generated_pdfs)} файлів")
        merged_file = self.output_dir / "ALL_WRITEUPS_MERGED.pdf"
        if merged_file.exists():
            print(f"🔗 Об'єднаний PDF: {merged_file.name}")


def check_dependencies():
    """Перевіряє наявність необхідних бібліотек"""
    dependencies = [
        ('playwright', 'playwright'),
        ('markdown', 'markdown'),
        ('PIL', 'Pillow')
    ]

    optional_dependencies = [
        ('PyPDF2', 'PyPDF2'),
        ('reportlab', 'reportlab')
    ]

    missing_packages = []
    missing_optional = []

    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    for import_name, package_name in optional_dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing_optional.append(package_name)

    if missing_packages:
        print("❌ Відсутні обов'язкові пакети:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nВстановіть їх командами:")
        print(f"pip install {' '.join(missing_packages)}")
        if 'playwright' in missing_packages:
            print("playwright install")
        return False

    if missing_optional:
        print("⚠️  Відсутні опціональні пакети (для об'єднання PDF):")
        for package in missing_optional:
            print(f"  - {package}")
        print(f"Встановіть їх: pip install {' '.join(missing_optional)}")
        print("Без них скрипт працюватиме, але не зможе об'єднувати PDF\n")

    return True


async def main():
    if len(sys.argv) < 3:
        print("Використання:")
        print("python3 main.py <шлях_до_репозиторію> <папка_для_PDF>")
        print("\nПриклади:")
        print("python3 main.py /Users/serhiitsybulnik/cyber-apocalypse-2025/forensics/ writeups_1")
        print("python3 main.py /Users/serhiitsybulnik/business-ctf-2025/forensics my_writeups")
        sys.exit(1)

    # Перевіряємо залежності
    if not check_dependencies():
        sys.exit(1)

    repo_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(repo_path):
        print(f"❌ Шлях не існує: {repo_path}")
        sys.exit(1)

    print(f"📂 Вхідна папка: {repo_path}")
    print(f"📁 Вихідна папка: {output_dir}")

    converter = CTFWriteupConverter(repo_path, output_dir)
    await converter.run()


if __name__ == "__main__":
    asyncio.run(main())

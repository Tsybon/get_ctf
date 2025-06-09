#!/usr/bin/env python3
"""
CTF Writeups to PDF Converter (Playwright version)
Автоматично конвертує всі writeup'и з GitHub репозиторію в PDF файли
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

class CTFWriteupConverter:
    def __init__(self, repo_path, output_dir="pdf_writeups"):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def find_challenge_folders(self):
        """Знаходить всі папки з задачами (які містять README.md)"""
        challenges = []
        
        # Перевіряємо чи передали шлях до конкретної категорії (наприклад forensics)
        if self.repo_path.name in ['forensics', 'web', 'crypto', 'pwn', 'misc', 'rev']:
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
            img_path = match.group(1)
            
            # Якщо це відносний шлях до assets
            if img_path.startswith('assets/') or img_path.startswith('./assets/'):
                img_name = img_path.split('/')[-1]
                full_img_path = assets_dir / img_name
                
                if full_img_path.exists():
                    try:
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
                            '.svg': 'image/svg+xml'
                        }
                        mime_type = mime_types.get(ext, 'image/png')
                        
                        # Створюємо base64 data URL
                        base64_data = base64.b64encode(img_data).decode('utf-8')
                        return f'![{match.group(2) if len(match.groups()) > 1 else ""}](data:{mime_type};base64,{base64_data})'
                        
                    except Exception as e:
                        print(f"Помилка обробки зображення {full_img_path}: {e}")
                        return match.group(0)  # Повертаємо оригінальний текст
            
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
        
        print(f"\n✅ Завершено! Успішно конвертовано: {success_count}/{len(challenges)} задач")
        print(f"📁 Файли збережено в: {self.output_dir.absolute()}")


def check_dependencies():
    """Перевіряє наявність необхідних бібліотек"""
    dependencies = [
        ('playwright', 'playwright'),
        ('markdown', 'markdown'),
        ('PIL', 'Pillow')
    ]
    
    missing_packages = []
    
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Відсутні необхідні пакети:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nВстановіть їх командами:")
        print(f"pip install {' '.join(missing_packages)}")
        if 'playwright' in missing_packages:
            print("playwright install")
        return False
    
    return True


async def main():
    if len(sys.argv) < 2:
        print("Використання:")
        print("python ctf_converter.py <шлях_до_репозиторію> [папка_для_PDF]")
        print("\nПриклад:")
        print("python ctf_converter.py /Users/serhiitsybulnik/cyber-apocalypse-2025/forensics/")
        sys.exit(1)
    
    # Перевіряємо залежності
    if not check_dependencies():
        sys.exit(1)
    
    repo_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "pdf_writeups"
    
    if not os.path.exists(repo_path):
        print(f"❌ Шлях не існує: {repo_path}")
        sys.exit(1)
    
    converter = CTFWriteupConverter(repo_path, output_dir)
    await converter.run()


if __name__ == "__main__":
    asyncio.run(main())

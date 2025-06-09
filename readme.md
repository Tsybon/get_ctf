CTF Writeups to PDF Converter
Автоматично конвертує CTF writeup'и з markdown в PDF файли для подальшого використання в NotebookLM.
Що робить:

🔍 Сканує папки з CTF задачами (автовизначення структури)
📝 Конвертує README.md файли в PDF з красивим форматуванням
🖼️ Вбудовує зображення з папок assets/ прямо в PDF (base64)
📋 Створює індексний файл зі списком всіх задач
🎨 Застосовує професійні CSS стили для коду та тексту

Використання:
bashpip install playwright markdown Pillow
playwright install
python3 main.py /path/to/ctf/repo/
Приклад структури:
forensics/
├── Challenge 1/
│   ├── README.md
│   └── assets/
└── Challenge 2/...
Результат:
pdf_writeups/
├── _INDEX.pdf
├── forensics_Challenge_1.pdf
└── forensics_Challenge_2.pdf
Ідеально для створення бази знань CTF розв'язків у NotebookLM! 🚀

# 🧠 CTF Writeups to PDF Converter

**Автоматичний конвертер CTF writeup'ів з Markdown у PDF**  
Ідеально підходить для подальшого використання в [NotebookLM](https://notebooklm.google)!

---

## 🔧 Що робить

- 🔍 Сканує папки з CTF задачами (автовизначення структури)
- 📝 Конвертує `README.md` файли у PDF з красивим форматуванням
- 🖼️ Вбудовує зображення з папок `assets/` прямо в PDF (через base64)
- 📋 Створює індексний файл зі списком усіх задач
- 🎨 Застосовує професійні CSS стилі для коду та тексту

---

## 🚀 Використання

1. Встанови необхідні залежності:

```
pip install playwright markdown Pillow
playwright install
```

2. Запусти конвертацію:

```
python3 main.py /path/to/ctf/repo/
```

📁 Приклад структури

```
forensics/
├── Challenge 1/
│   ├── README.md
│   └── assets/
└── Challenge 2/
```

📄 Результат

```
pdf_writeups/
├── _INDEX.pdf
├── forensics_Challenge_1.pdf
└── forensics_Challenge_2.pdf
```

✅ Навіщо це потрібно?
Цей інструмент ідеально підходить для:

📚 Створення бази знань CTF-рішень

🧾 Упорядкування writeup'ів для презентацій або архівування

💡 Імпорту в NotebookLM для швидкого доступу до знань

Прискорюй розвиток своїх навичок у CTF! 🔐🚀

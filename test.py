import json
import os
from whoosh import index, writing
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import MultifieldParser

# Параметры
DB_JSON_PATH = "data/documents.json"  # Путь к вашему JSON-файлу
INDEX_DIR = "indexdir"               # Папка для Whoosh-индекса

# 1. Определяем схему для Whoosh
schema = Schema(
    id=ID(stored=True, unique=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True)
)

# 2. Создаём или открываем индекс
if not os.path.exists(INDEX_DIR):
    os.mkdir(INDEX_DIR)
    ix = index.create_in(INDEX_DIR, schema)
else:
    ix = index.open_dir(INDEX_DIR)

# 3. Функция для (пере)индексации всех документов из JSON
def build_index(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    writer = ix.writer()
    # Если нужно обновить - очистим старый индекс
    writer.mergetype = writing.CLEAR

    for doc in docs:
        doc_id = str(doc.get("id", docs.index(doc)))
        writer.add_document(
            id=doc_id,
            title=doc.get("title", ""),
            content=doc.get("content", "")
        )
    writer.commit()
    print(f"Indexed {len(docs)} documents.")

# 4. Поиск по ключевому слову в полях title и content
def search(query_str, top_n=10):
    parser = MultifieldParser(["title", "content"], schema=ix.schema)
    q = parser.parse(query_str)

    with ix.searcher() as searcher:
        results = searcher.search(q, limit=top_n)
        print(f"Found {len(results)} results for '{query_str}':")
        for hit in results:
            print(f"- ID: {hit['id']} | Title: {hit['title']}")
            # По желанию можно вывести часть контента:
            # print(hit.highlights("content"))

# 5. Пример использования
if __name__ == "__main__":
    # Сначала (пере)индексируем базу
    build_index(DB_JSON_PATH)

    # Ищем по любому слову
    while True:
        query_text = input("Enter search query (or 'exit'): ")
        if query_text.lower() == 'exit':
            break
        search(query_text)

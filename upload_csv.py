import csv
import json

CSV_FILE = "products.csv"
JSON_FILE = "products.json"

products = []

with open(CSV_FILE, mode="r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        row["price"] = float(row["price"])  # Garante que preço seja numérico
        products.append(row)

with open(JSON_FILE, mode="w", encoding="utf-8") as file:
    json.dump(products, file, indent=4, ensure_ascii=False)

print(f"✅ CSV convertido para JSON: {JSON_FILE}")

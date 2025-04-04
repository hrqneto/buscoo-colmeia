import csv
from typing import List, Dict, Tuple  # já tem, só confirmar

def salvar_relatorio_erros(erros: List[Dict], caminho="report.csv"):
    with open(caminho, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["produto", "motivo", "dados"])
        writer.writeheader()
        writer.writerows(erros)

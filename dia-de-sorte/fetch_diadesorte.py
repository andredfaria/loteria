import json
import os
import time
import requests

BASE_URL = "https://loteriascaixa-api.herokuapp.com/api/diadesorte"
DADOS_DIR = os.path.join(os.path.dirname(__file__), "dados")
DELAY_ENTRE_REQUESTS = 0.3  # segundos


def get_latest_concurso():
    resp = requests.get(f"{BASE_URL}/latest", timeout=10)
    resp.raise_for_status()
    return resp.json()["concurso"]


def get_ultimo_salvo():
    numeros = []
    for nome in os.listdir(DADOS_DIR):
        if nome.startswith("diadesorte_") and nome.endswith(".json"):
            try:
                n = int(nome.replace("diadesorte_", "").replace(".json", ""))
                numeros.append(n)
            except ValueError:
                pass
    return max(numeros) if numeros else 0


def fetch_concurso(n):
    try:
        resp = requests.get(f"{BASE_URL}/{n}", timeout=10)
        if resp.status_code == 404:
            print(f"  WARN: concurso {n} não encontrado (404)")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        print(f"  ERROR: concurso {n} falhou (timeout)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: concurso {n} falhou ({e})")
        return None


def salvar_concurso(n, data):
    path = os.path.join(DADOS_DIR, f"diadesorte_{n}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    os.makedirs(DADOS_DIR, exist_ok=True)

    print("Consultando último concurso na API...")
    latest = get_latest_concurso()
    inicio = get_ultimo_salvo() + 1

    print(f"Último concurso na API: {latest}")
    print(f"Último salvo localmente: {inicio - 1}")

    if inicio > latest:
        print("Base de dados já está atualizada.")
        return

    total = latest - inicio + 1
    print(f"Buscando concursos {inicio} a {latest} ({total} no total)...\n")

    salvos = 0
    erros = 0

    for i, n in enumerate(range(inicio, latest + 1), start=1):
        path = os.path.join(DADOS_DIR, f"diadesorte_{n}.json")
        if os.path.exists(path):
            print(f"  [{i}/{total}] diadesorte_{n}.json já existe, pulando")
            salvos += 1
            continue

        data = fetch_concurso(n)
        if data is not None:
            salvar_concurso(n, data)
            print(f"  [{i}/{total}] diadesorte_{n}.json ✓")
            salvos += 1
        else:
            erros += 1

        time.sleep(DELAY_ENTRE_REQUESTS)

    print(f"\nConcluído: {salvos} salvos, {erros} erros.")


if __name__ == "__main__":
    main()

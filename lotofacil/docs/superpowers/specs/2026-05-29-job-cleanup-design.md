# Job Cleanup — Design Spec

**Data:** 2026-05-29  
**Status:** Aprovado  
**Limitação resolvida:** #2 — `job_output` e `job_status` crescem indefinidamente no SQLite

---

## Contexto

`TreinoRegistry` persiste saída de jobs em `treinos.db` com duas tabelas:
- `job_status` — uma linha por job (task_id, done, success, finished_at)
- `job_output` — N linhas por job (cada linha de stdout)

Não há nenhum mecanismo de limpeza. Em uso contínuo, essas tabelas crescem para sempre.

A tabela `job_status` não tem `created_at`, apenas `finished_at` (jobs ativos têm `finished_at = NULL`).

---

## Solução

### 1. Adicionar `created_at` ao schema de `job_status`

O schema atual não tem data de criação. A migration é necessária para ordenar jobs por idade ao aplicar o limite de contagem.

**No `_SCHEMA`:** adicionar coluna com `DEFAULT (datetime('now'))`.  
**Migration para bancos existentes:** `ALTER TABLE job_status ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'))` — executado uma vez na inicialização, ignorado se a coluna já existir.

### 2. Método `_purge_old_jobs(max_age_days=7, max_jobs=200)`

Adicionado a `TreinoRegistry`. Chamado no início de `create_job()` (lazy cleanup).

**Lógica em uma transação:**

```python
# Requires: from datetime import datetime, timezone, timedelta  (already imported)
def _purge_old_jobs(self, max_age_days: int = 7, max_jobs: int = 200) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    with self._conn() as conn:
        # Jobs finalizados e expirados
        old = conn.execute(
            "SELECT task_id FROM job_status WHERE done = 1 AND finished_at < ?",
            (cutoff,)
        ).fetchall()

        # Jobs excedentes ao limite (mais antigos primeiro, excluindo ativos)
        excess = conn.execute(
            """SELECT task_id FROM job_status WHERE done = 1
               ORDER BY created_at ASC
               LIMIT MAX(0,
                 (SELECT COUNT(*) FROM job_status WHERE done = 1) - ?
               )""",
            (max_jobs,)
        ).fetchall()

        to_delete = list({r[0] for r in old + excess})
        if not to_delete:
            return
        ph = ",".join("?" * len(to_delete))
        conn.execute(f"DELETE FROM job_output WHERE task_id IN ({ph})", to_delete)
        conn.execute(f"DELETE FROM job_status WHERE task_id IN ({ph})", to_delete)
        conn.commit()
```

**Invariante:** jobs com `done = 0` (ainda rodando) nunca são deletados, mesmo que excedam o limite.

### 3. Chamada em `create_job()`

```python
def create_job(self, task_id: str) -> None:
    self._purge_old_jobs()  # lazy cleanup
    with self._conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_status (task_id, done, created_at) VALUES (?, 0, ?)",
            (task_id, _now()),
        )
        conn.commit()
```

---

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/lotofacil/interface/painel/treino_registry.py` | Adicionar `created_at` ao schema + migration + `_purge_old_jobs()` + atualizar `create_job()` |
| `src/lotofacil/interface/painel/tests/test_server.py` ou novo `tests/test_treino_registry.py` | 3 testes para `_purge_old_jobs` |

**Sem mudanças em `server.py` ou `dashboard.html`.**

---

## Testes

```python
def test_purge_remove_jobs_antigos():
    # Cria jobs com finished_at 8 dias atrás → devem ser removidos

def test_purge_remove_jobs_excedentes():
    # Cria 205 jobs finalizados → após purge, máximo 200

def test_purge_preserva_jobs_ativos():
    # Job sem done=1 não é removido mesmo que antigo
```

---

## O que não muda

- Interface do `TreinoRegistry` para `server.py` — nenhuma chamada nova necessária
- Dados de treinos na tabela `treinos` — não são afetados
- Dados de `jogos_gerados` — não são afetados

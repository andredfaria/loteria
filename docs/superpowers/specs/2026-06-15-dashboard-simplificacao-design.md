# Design: Simplificação do Dashboard Lotofácil

**Data:** 2026-06-15
**Escopo:** Interface web (`dashboard.html` + lógica JS associada)
**Arquivo alvo:** `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`

---

## Contexto

O dashboard atual tem 3744 linhas em um único arquivo HTML/CSS/JS e 5 abas na sidebar (Coleta, Dados, Modelos, Validação, ROI Lab). O usuário relatou dois problemas principais:

1. **Muita coisa na tela ao mesmo tempo** — difícil saber onde focar
2. **Navegação confusa** — várias abas que não são usadas no dia a dia

O fluxo real do usuário é: **Coleta → Treinar modelo → Gerar jogo**. Tudo mais é ocasional.

---

## Objetivos

- Reduzir o ruído visual sem remover funcionalidade
- Tornar o fluxo core (Coleta + Treinar + Gerar) imediato e sem distrações
- Mover funcionalidades avançadas (Dados, Validação, ROI Lab) para fora do caminho principal
- Console de log vira painel lateral sob demanda

---

## O que NÃO muda

- Todas as rotas de API do servidor Flask permanecem intactas
- Nenhuma funcionalidade é removida — apenas reorganizada
- Estrutura de arquivos do projeto não muda

---

## Design

### 1. Sidebar — Nova Navegação

**Antes:** 5 abas planas (Coleta, Dados, Modelos, Validação, ROI Lab)

**Depois:**
```
📥  Coleta
🧠  Modelos
──────────────
⚙️  Avançado  ▸
    🗃️  Dados
    ✅  Validação
    🧪  ROI Lab
```

- "Avançado" é um item expansível. Ao clicar, exibe os sub-itens com indentação e fonte menor
- Estado expandido/colapsado persiste em `localStorage` com chave `sidebar_advanced_open`
- Sub-itens têm a mesma funcionalidade de sempre — só estão um nível abaixo

### 2. Aba Modelos — Reorganização Interna

O conteúdo atual da aba Modelos é denso e mistura responsabilidades. A nova versão divide em duas seções verticais sequenciais:

#### Seção A — Treinar

- Cards de configuração de modelo (Base, +Lua, +Clima, +Lua+Clima) com visual mais limpo
- Parâmetros opcionais (epochs, window_size, seed, fast mode) ficam dentro de um `<details>` com texto "Opções avançadas ▸", colapsado por padrão
- Botão **Iniciar Treino** habilitado somente quando um card de configuração está selecionado
- Logo abaixo do botão: lista de treinos (em andamento, concluídos, com falha) com ações de retry/cancelar/deletar

#### Seção B — Gerar Jogo

- Separada da seção anterior por um `<hr>` com título "Gerar Jogo"
- Lista apenas modelos com `status === "completed"` disponíveis para uso
- Ao selecionar um modelo: exibe dois campos simples — nº de jogos (1–20, padrão 1) e nº de números (11 ou 15, padrão 15)
- Botão **Gerar** dispara a chamada ao endpoint existente `/api/treinos/<id>/gerar`
- Resultado aparece inline: números do jogo em destaque, e se o concurso já ocorreu, mostra acertos com highlight

Métricas de qualidade (hits distribution, p-value, leaderboard) são removidas da aba Modelos e ficam acessíveis somente via Avançado → Validação.

### 3. Console Lateral — Painel Deslizante

**Antes:** Painel fixo ocupando ~50% da altura da tela, sempre visível

**Depois:** Painel overlay deslizante da direita

- **Trigger:** ícone `⌨ Log` fixo no canto inferior direito da tela (posição fixa, z-index alto)
- **Badge:** mostra contagem de tarefas em execução (ex: `⌨ 2`). Quando 0, apenas o ícone
- **Abertura:** manual (clique no ícone) ou automática quando um comando é disparado
- **Largura:** ~35% da tela em desktop, 100% em mobile
- **Fechamento:**
  - Manual: botão ✕ no cabeçalho do painel
  - Automático (sucesso): fecha após 3 segundos com toast de confirmação
  - Erro: permanece aberto para leitura do log
- **Mobile:** o console vira uma aba dedicada no bottom nav em vez de painel lateral

---

## Componentes Afetados

| Componente | Mudança |
|---|---|
| Sidebar HTML/JS | Adicionar item "Avançado" expansível, remover abas Dados/Validação/ROI Lab do nível raiz |
| `switchTab()` | Suportar sub-abas de Avançado |
| `renderModelosPage()` | Dividir em seções Treinar e Gerar Jogo com nova hierarquia visual |
| Console section | Remover do layout principal, implementar como overlay lateral |
| Bottom nav (mobile) | Adicionar aba Console; sub-itens de Avançado via sheet ou modal |
| CSS | Novos estilos para sidebar expandível, painel lateral, badge de tarefas |

---

## Critérios de Sucesso

1. Sidebar mostra apenas 3 itens no estado padrão (Coleta, Modelos, Avançado)
2. Clicar em Avançado expande sub-itens; estado persiste ao recarregar
3. Aba Modelos mostra claramente duas seções: Treinar e Gerar Jogo
4. Console não ocupa espaço quando fechado
5. Badge mostra número de tarefas em execução
6. Ao disparar um comando, console abre automaticamente
7. Ao concluir com sucesso, console fecha após 3s com toast
8. Ao concluir com erro, console permanece aberto
9. Todas as funcionalidades existentes continuam acessíveis

---

## Fora de Escopo

- Refatoração do servidor Flask ou das rotas de API
- Mudanças na aba Coleta (permanece como está)
- Mudanças nas abas Dados, Validação, ROI Lab (permanecem funcionalmente iguais, só mudam de posição na nav)
- Separação do `dashboard.html` em múltiplos arquivos

# Lotofácil Dashboard — Design System

> **Para agentes de IA:** Leia este arquivo **antes** de qualquer modificação no `dashboard.html`. Toda decisão de design aqui é definitiva. Não introduza padrões que conflitem com o que está descrito.

---

## 1. Tokens de Design (CSS Variables)

Todos os valores visuais vivem em `:root` no `dashboard.html`. **Nunca use hex ou valores literais fora das variáveis.**

| Token | Valor | Uso |
|-------|-------|-----|
| `--bg` | `#0f172a` | Fundo principal da página |
| `--surface` | `#1e293b` | Cards, navbar, sidebar, console |
| `--surface-2` | `#273549` | Inputs, botões secundários |
| `--border` | `#334155` | Divisórias padrão |
| `--border-light` | `rgba(255,255,255,0.06)` | Divisórias sutis em tabelas |
| `--text` | `#e2e8f0` | Texto principal |
| `--muted` | `#94a3b8` | Labels, metadados |
| `--dim` | `#64748b` | Texto desabilitado, separadores |
| `--accent` | `#38bdf8` | Azul interativo (links, ativos, foco) |
| `--accent-dim` | `#0f2942` | Fundo de elementos com accent |
| `--accent-glow` | `rgba(56,189,248,0.12)` | Hover em linhas de tabela |
| `--green` | `#4ade80` | Sucesso, online, números pares |
| `--red` | `#f87171` | Erro, falha |
| `--yellow` | `#fbbf24` | Aviso, loading |
| `--orange` | `#fb923c` | Animação de borda pulsante |
| `--purple` | `#a78bfa` | Labels lab, números ímpares |
| `--radius` | `0.5rem` | Borda padrão |
| `--radius-lg` | `0.75rem` | Modais, cards maiores |
| `--radius-xl` | `1rem` | Bottom sheet (mobile) |
| `--transition` | `0.2s ease` | Todas as transições CSS |
| `--nav-h` | `56px` | Altura da navbar |
| `--bottom-nav-h` | `56px` | Altura da navegação inferior (mobile) |
| `--sidebar-w` | `180px` | Largura da sidebar (desktop) |

---

## 2. Breakpoints (Mobile-First)

O sistema usa **mobile-first**: estilos base para mobile, `min-width` para desktop.

| Breakpoint | Largura | Comportamento |
|-----------|---------|---------------|
| Base (mobile) | `< 768px` | Bottom tab bar visível, sidebar oculta |
| Tablet / Desktop | `≥ 768px` | Sidebar visível, bottom tab bar oculta |

**Regra:** Use sempre `@media (min-width: 768px)` para escalar para desktop. **Nunca** use `max-width` para sobrescrever estilos base desktop — isso inverte a lógica mobile-first.

---

## 3. Navegação

### Desktop (≥ 768px)
- **Sidebar esquerda** (`.sidebar`, largura `--sidebar-w: 180px`)
- Itens com ícone + label; estado ativo com `background: var(--accent-dim); color: var(--accent)`

### Mobile (< 768px)
- **Bottom tab bar** (`.bottom-nav`, altura `--bottom-nav-h`)
- Fixo no fundo da tela; os mesmos 4 itens da sidebar
- `padding-bottom: var(--bottom-nav-h)` no `.layout` para compensar
- Max 4–5 itens (conforme Material Design guideline `bottom-nav-limit`)

**Como trocar de aba:** chame sempre `switchTab(id)`. Ela sincroniza sidebar E bottom nav automaticamente.

```javascript
// Correto — sincroniza ambos
switchTab('predicao');

// Errado — atualiza só um dos dois
document.querySelector('.sidebar .tab').classList.add('active');
```

---

## 4. Componentes

### Botões (`.action-btn`)

```css
/* Base */
padding: 0.4rem 0.85rem; font-size: 0.78rem;
border: 1px solid var(--border); background: var(--surface-2);
border-radius: var(--radius); transition: all var(--transition);
```

**No mobile**, o media query já aplica `min-height: 44px` e `padding: 0.6rem 1rem`. **Não remova isso.**

Estados obrigatórios:
- `:hover` → `border-color: var(--accent); background: var(--accent-dim); color: var(--accent)`
- `:disabled` → `opacity: 0.35; cursor: not-allowed`
- `.running` → borda pulsante amarela (animação `pulse-border`)

### Inputs e Selects

```css
background: var(--surface-2); border: 1px solid var(--border);
border-radius: var(--radius); padding: 0.35rem 0.6rem;
color: var(--text); font-size: 0.8rem;
```

**Regra crítica para mobile:** inputs DEVEM ter `font-size: 1rem` (16px) em `@media (max-width: 767px)`. Valores abaixo de 16px acionam auto-zoom do iOS, quebrando o layout. O media query existente já cobre isso — nunca remova.

### Tabelas (`.dados-table-wrap`)

Sempre envolvidas em um container com `overflow-x: auto` no mobile. Quando adicionar novas tabelas:

```html
<!-- Estrutura padrão -->
<div class="dados-table-wrap">
  <table>...</table>
</div>
```

O media query de mobile aplica `overflow-x: auto` e `min-width: 580px` na tabela. Para tabelas novas, verifique se o `min-width` é adequado ao número de colunas.

### Cards de Grid

Use `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` no desktop. No mobile o media query já força `1fr`. Não adicione `min-width` fixo em cards sem verificar o comportamento em 375px.

### Toasts

- Posição: `bottom-right` no desktop; `bottom: calc(--bottom-nav-h + 0.75rem)` no mobile (fica acima da bottom nav)
- Auto-dismiss: 3–5s
- Variantes: `.success` (borda verde), `.error` (borda vermelha), `.info` (borda accent)

### Modal

- Desktop: centralizado, `max-width: 600px`, `max-height: 80vh`
- Mobile: **bottom sheet** — `border-radius: var(--radius-xl) var(--radius-xl) 0 0`, `max-height: 88vh`, alinhado ao fundo

---

## 5. Tipografia

| Contexto | Tamanho | Peso |
|---------|---------|------|
| Labels uppercase | `0.68–0.72rem` | 600 |
| Corpo (muted/meta) | `0.78–0.8rem` | 400 |
| Corpo padrão | `0.82–0.85rem` | 400–500 |
| Títulos de seção | `1rem–1.1rem` | 600–700 |
| Console/monospace | `0.78rem` | 400 |
| **Inputs (mobile)** | **1rem (16px)** | — |

**Font stack:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`  
**Monospace:** `'SF Mono', 'Fira Code', 'Cascadia Code', monospace`

---

## 6. Ícones

O dashboard usa **emojis** como ícones por ser um único arquivo HTML sem build step. Isso é uma decisão deliberada de portabilidade (sem dependências externas).

**Regra:** Mantenha emojis consistentes com o padrão já estabelecido. Não misture emojis com SVG inline sem converter todos.

| Aba | Emoji |
|-----|-------|
| Coleta | 📥 |
| Dados | 🗃️ |
| Predição | 🤖 |
| Validação | ✅ |

Se o projeto migrar para build step com bundler, substituir por **Lucide Icons** (`lucide-react` ou SVG inline) — família stroke, stroke-width 1.5, tamanho 20px.

---

## 7. Regras de Ouro (não negocie)

1. **Mobile-first sempre:** estilos base = mobile. Desktop via `min-width`.
2. **44px touch targets:** todo elemento clicável precisa de `min-height: 44px` no mobile.
3. **16px inputs:** `font-size: 1rem` em todos os inputs no mobile (previne zoom iOS).
4. **Tokens, nunca hex:** use variáveis CSS. Nenhum `#hex` novo fora do `:root`.
5. **switchTab() é a única API de navegação:** não mexa diretamente nas classes `.active` de `.sidebar` ou `.bottom-nav`.
6. **Overflow-x em tabelas:** toda tabela nova deve ser envolvida em `.dados-table-wrap` ou ter `overflow-x: auto` no mobile.
7. **Toasts acima da bottom nav:** use `calc(var(--bottom-nav-h) + offset)` para posicionar.
8. **Animações via transform/opacity:** nunca anime `width`, `height`, `top`, `left` — causa layout thrashing.
9. **`var(--transition)`:** toda transição usa `0.2s ease`. Não crie valores ad-hoc.
10. **Nada de inline styles com cores:** se precisar de cor inline, crie uma variável ou classe.

---

## 8. Estrutura do Arquivo

O `dashboard.html` é um arquivo único deliberadamente (sem build step, portável via Docker). Estrutura interna:

```
<head>
  <style>
    1. Reset + :root (tokens)
    2. Componentes por ordem de uso (navbar, layout, sidebar, ...)
    3. Bottom Nav
    4. @media (max-width: 767px)  ← mobile overrides
    5. @media (min-width: 768px)  ← tablet/desktop confirmations
  </style>
</head>
<body>
  <nav.navbar>
  <div.layout>
    <aside.sidebar>
    <div.main>
      <div.actions-bar>
      <div.content-split>
        <div.numbers-section>
        <div.console-section>
  <div.modal-overlay>
  <div.toast-container>
  <nav.bottom-nav>   ← mobile navigation (always last before <script>)
  <script>
    STATE, LOGGING, INIT, CONSOLE, SIDEBAR, COMMANDS, RUN, SSE,
    STATUS, DADOS, PREDICAO, VALIDACAO, TREINOS, MODAL, TOAST, START
  </script>
</body>
```

**Ordem das seções JS** (nunca reordene — dependências implícitas):
1. `STATE` e constantes
2. `LOGGING` (logClient, error handlers)
3. `INIT` (init function)
4. `CONSOLE PERSISTENCE`
5. `SIDEBAR` (buildSidebar, buildBottomNav, switchTab)
6. `COMMANDS / ACTIONS`
7. `RUN COMMAND` + `SSE` (listenStream)
8. `STATUS` (loadStatus)
9. Features por aba (DADOS, PREDICAO, VALIDACAO)
10. `MODAL` + `TOAST`
11. `START` (DOMContentLoaded)

---

## 9. Checklist antes de qualquer PR

- [ ] Testado em 375px de largura (iPhone SE)
- [ ] Bottom nav visível e funcional em mobile
- [ ] Nenhum scroll horizontal na viewport (exceto tabelas intencionais)
- [ ] Touch targets ≥ 44px em todos os elementos clicáveis
- [ ] Inputs com `font-size: 1rem` no mobile (não causam zoom iOS)
- [ ] Toasts visíveis acima da bottom nav
- [ ] Modal abre como bottom sheet em mobile
- [ ] Nenhum hex literal novo fora do `:root`
- [ ] `switchTab()` usado para toda troca de aba
- [ ] Sem `@media (max-width: ...)` para estilos novos (use `min-width`)

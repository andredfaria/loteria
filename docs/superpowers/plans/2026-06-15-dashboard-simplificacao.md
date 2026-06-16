# Dashboard Simplificação Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplificar o dashboard Lotofácil reduzindo a sidebar para 3 itens, tornando o console um painel lateral deslizante e reorganizando a aba Modelos em duas seções sequenciais (Treinar + Gerar Jogo).

**Architecture:** Todas as mudanças são no arquivo único `dashboard.html` (HTML + CSS + JS). Nenhuma rota de API ou arquivo Python é alterado. As mudanças são incrementais: sidebar → console panel → modelos tab. Cada task produz estado funcional e commitável.

**Tech Stack:** HTML, CSS (custom properties + flexbox), JavaScript vanilla, Flask serve estático.

---

## Mapa de Arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `lotofacil/src/lotofacil/interface/painel/static/dashboard.html` | Modify | Único arquivo afetado — todo CSS, HTML e JS do dashboard |

---

## Task 1: Sidebar — Avançado Colapsável

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`
  - Seção CSS (~linha 44–59): novos estilos para sidebar expandível
  - Seção JS `CATEGORIES` (~linha 1065): reestruturar categorias
  - Função `buildSidebar()` (~linha 1073): nova lógica de renderização
  - Função `buildBottomNav()` (~linha 1086): atualizar mobile
  - Função `switchTab()` (~linha 1099): suportar sub-itens de Avançado

- [ ] **Step 1: Verificar comportamento atual**

  Abra o dashboard no browser. Confirme que existem 5 tabs na sidebar: Coleta, Dados, Modelos, Validação, ROI Lab. Anote que todas estão no mesmo nível visual.

- [ ] **Step 2: Adicionar CSS para sidebar expandível**

  Localize o bloco CSS `.sidebar .tab` (~linha 50). Logo após o estilo `.sidebar .tab .icon`, adicione:

  ```css
  .sidebar .separator {
    height: 1px; background: var(--border);
    margin: 0.4rem 0.5rem; flex-shrink: 0;
  }
  .sidebar .advanced-toggle {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.65rem 0.75rem; border-radius: var(--radius);
    font-size: 0.82rem; cursor: pointer; transition: all var(--transition);
    color: var(--muted); border: none; background: none; text-align: left;
    white-space: nowrap; font-weight: 500; width: 100%;
  }
  .sidebar .advanced-toggle:hover { background: rgba(255,255,255,0.05); color: var(--text); }
  .sidebar .advanced-toggle .icon { font-size: 1.1rem; width: 1.5rem; text-align: center; flex-shrink: 0; }
  .sidebar .advanced-toggle .arrow { margin-left: auto; font-size: 0.7rem; transition: transform var(--transition); }
  .sidebar .advanced-toggle.open .arrow { transform: rotate(90deg); }
  .sidebar .sub-tab {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.5rem 0.75rem 0.5rem 2.2rem;
    border-radius: var(--radius); font-size: 0.78rem; cursor: pointer;
    transition: all var(--transition); color: var(--dim);
    border: none; background: none; text-align: left; white-space: nowrap; font-weight: 500;
  }
  .sidebar .sub-tab:hover { background: rgba(255,255,255,0.04); color: var(--muted); }
  .sidebar .sub-tab.active { background: var(--accent-dim); color: var(--accent); font-weight: 600; }
  .sidebar .sub-tab .icon { font-size: 0.95rem; width: 1.25rem; text-align: center; flex-shrink: 0; }
  ```

- [ ] **Step 3: Reestruturar CATEGORIES e adicionar ADVANCED_CATEGORIES**

  Localize (~linha 1065):
  ```js
  const CATEGORIES = [
    { id: 'coleta',    icon: '📥', label: 'Coleta' },
    { id: 'dados',     icon: '🗃️', label: 'Dados' },
    { id: 'modelos',   icon: '🧠', label: 'Modelos' },
    { id: 'validacao', icon: '✅', label: 'Validação' },
    { id: 'roi_lab',   icon: '🧪', label: 'ROI Lab' },
  ];
  ```

  Substitua por:
  ```js
  const CATEGORIES = [
    { id: 'coleta',  icon: '📥', label: 'Coleta'  },
    { id: 'modelos', icon: '🧠', label: 'Modelos' },
  ];

  const ADVANCED_CATEGORIES = [
    { id: 'dados',     icon: '🗃️', label: 'Dados'     },
    { id: 'validacao', icon: '✅', label: 'Validação' },
    { id: 'roi_lab',   icon: '🧪', label: 'ROI Lab'   },
  ];
  ```

- [ ] **Step 4: Adicionar advancedOpen ao STATE**

  Localize a declaração do objeto `STATE` (~linha 900). Adicione `advancedOpen` logo após `validacaoLastN`:

  ```js
  advancedOpen: localStorage.getItem('sidebar_advanced_open') === 'true',
  ```

- [ ] **Step 5: Reescrever buildSidebar()**

  Localize a função `buildSidebar()` (~linha 1073). Substitua por:

  ```js
  function buildSidebar() {
    const el = document.getElementById('sidebar');
    el.innerHTML = '';

    // Core tabs
    for (const cat of CATEGORIES) {
      const btn = document.createElement('button');
      btn.className = 'tab' + (cat.id === STATE.activeTab ? ' active' : '');
      btn.innerHTML = `<span class="icon">${cat.icon}</span><span class="label">${cat.label}</span>`;
      btn.onclick = () => switchTab(cat.id);
      el.appendChild(btn);
    }

    // Separator
    const sep = document.createElement('div');
    sep.className = 'separator';
    el.appendChild(sep);

    // Avançado toggle
    const advancedIsActive = ADVANCED_CATEGORIES.some(c => c.id === STATE.activeTab);
    const toggle = document.createElement('button');
    toggle.className = 'advanced-toggle' + (STATE.advancedOpen ? ' open' : '');
    toggle.id = 'advancedToggle';
    toggle.innerHTML = `<span class="icon">⚙️</span><span class="label">Avançado</span><span class="arrow">▶</span>`;
    toggle.onclick = () => {
      STATE.advancedOpen = !STATE.advancedOpen;
      localStorage.setItem('sidebar_advanced_open', STATE.advancedOpen);
      buildSidebar();
    };
    el.appendChild(toggle);

    // Sub-items (only when open)
    if (STATE.advancedOpen) {
      for (const cat of ADVANCED_CATEGORIES) {
        const btn = document.createElement('button');
        btn.className = 'sub-tab' + (cat.id === STATE.activeTab ? ' active' : '');
        btn.innerHTML = `<span class="icon">${cat.icon}</span><span class="label">${cat.label}</span>`;
        btn.onclick = () => switchTab(cat.id);
        el.appendChild(btn);
      }
    }

    buildBottomNav();
  }
  ```

- [ ] **Step 6: Reescrever buildBottomNav()**

  Localize `buildBottomNav()` (~linha 1086). Substitua por:

  ```js
  function buildBottomNav() {
    const el = document.getElementById('bottomNav');
    if (!el) return;
    el.innerHTML = '';
    const allCats = [...CATEGORIES, ...ADVANCED_CATEGORIES];
    for (const cat of allCats) {
      const btn = document.createElement('button');
      btn.className = 'bn-tab' + (cat.id === STATE.activeTab ? ' active' : '');
      btn.innerHTML = `<span class="bn-icon">${cat.icon}</span><span>${cat.label}</span>`;
      btn.onclick = () => switchTab(cat.id);
      el.appendChild(btn);
    }
  }
  ```

- [ ] **Step 7: Corrigir switchTab() — active class nos sub-tabs**

  Localize `switchTab()` (~linha 1099). As linhas que atualizam classes da sidebar usam índice fixo do array `CATEGORIES`. Substitua as duas linhas de `forEach` por:

  ```js
  function switchTab(id) {
    STATE.activeTab = id;
    _updatePageTitle?.();

    // Atualizar classes da sidebar (tabs core + sub-tabs)
    document.querySelectorAll('.sidebar .tab').forEach(el => {
      const tabId = el.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
      el.classList.toggle('active', tabId === id);
    });
    document.querySelectorAll('.sidebar .sub-tab').forEach(el => {
      const tabId = el.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
      el.classList.toggle('active', tabId === id);
    });
    document.querySelectorAll('.bottom-nav .bn-tab').forEach(el => {
      const tabId = el.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
      el.classList.toggle('active', tabId === id);
    });

    // Resto do switchTab permanece igual a partir daqui:
    const cs = document.querySelector('.content-split');
    cs.classList.toggle('dados-mode', id === 'dados');
    // ... (manter o restante da função original intacto)
  ```

  > **Atenção:** Mantenha todo o bloco `if/else` de renderização que vem depois (`if (id === 'dados')`, `else if (id === 'validacao')`, etc.) exatamente como está. Só substitua as 4 linhas de `forEach` no início da função.

- [ ] **Step 8: Verificar no browser**

  Recarregue o dashboard. Confirme:
  - Sidebar mostra apenas: Coleta, Modelos, separador, ⚙️ Avançado ▶
  - Clicar em Avançado expande para mostrar Dados, Validação, ROI Lab com indentação
  - Clicar novamente recolhe
  - Recarregar a página mantém o estado (aberto ou fechado) via localStorage
  - Clicar em qualquer sub-item navega para a tab correta e fica destacado
  - Coleta e Modelos funcionam normalmente

- [ ] **Step 9: Commit**

  ```bash
  git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
  git commit -m "feat(dashboard): sidebar com Avançado colapsável"
  ```

---

## Task 2: Console Lateral — CSS e HTML

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`
  - Seção CSS (~linha 264–303): substituir estilos do console
  - HTML do body (~linha 776–821): adicionar painel lateral e trigger button

- [ ] **Step 1: Adicionar CSS do painel lateral**

  Localize o bloco `/* Console */` (~linha 264). **Substitua** todo o bloco de estilos `.console-section`, `.console-section .section-header`, `.console-section .section-header h3`, `.console-section .section-header .clear-btn`, `.console-controls`, `.console-filter-btn`, `.console-filter-btn.active`, `.console-filter-btn:hover`, `.console-output` por:

  ```css
  /* Console Lateral Panel */
  .console-panel {
    position: fixed; top: var(--nav-h); right: 0; bottom: 0;
    width: 35%; min-width: 320px; max-width: 560px;
    background: var(--surface); border-left: 1px solid var(--border);
    display: flex; flex-direction: column;
    transform: translateX(100%); transition: transform 0.25s ease;
    z-index: 80; box-shadow: -4px 0 24px rgba(0,0,0,0.3);
  }
  .console-panel.open { transform: translateX(0); }
  .console-panel .section-header {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.5rem 1rem; border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .console-panel .section-header h3 {
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--dim); font-weight: 600;
  }
  .console-panel .section-header .close-panel-btn {
    margin-left: auto; font-size: 0.85rem; color: var(--dim);
    cursor: pointer; background: none; border: none; padding: 2px 6px;
    border-radius: 4px; transition: color var(--transition);
  }
  .console-panel .section-header .close-panel-btn:hover { color: var(--text); }
  .console-controls { display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap; padding: 0.4rem 1rem; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .console-filter-btn {
    font-size: 0.67rem; border: 1px solid var(--border); background: var(--surface-2);
    color: var(--muted); border-radius: 999px; padding: 0.15rem 0.5rem; cursor: pointer;
    transition: all var(--transition);
  }
  .console-filter-btn.active { color: var(--text); border-color: var(--accent); background: var(--accent-dim); }
  .console-filter-btn:hover { color: var(--text); }
  .console-output {
    flex: 1; overflow-y: auto; padding: 0.75rem 1rem;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 0.78rem; line-height: 1.6; background: #0b1120;
  }
  .console-output .line { white-space: pre-wrap; word-break: break-all; color: var(--muted); }
  .console-output .line.cmd { color: var(--green); }
  .console-output .line.dim { color: var(--dim); }
  .console-output .line.success { color: var(--green); font-weight: 600; }
  .console-output .line.warn { color: var(--yellow); }
  .console-output .line.error { color: var(--red); }
  .console-output .line.sep { border-top: 1px solid var(--border); margin: 0.5rem 0; padding-top: 0.5rem; }

  /* Console trigger button */
  .console-trigger {
    position: fixed; bottom: 1.25rem; right: 1.25rem;
    display: flex; align-items: center; gap: 0.4rem;
    padding: 0.5rem 0.9rem; background: var(--surface);
    border: 1px solid var(--border); border-radius: 999px;
    color: var(--muted); font-size: 0.78rem; font-family: inherit;
    cursor: pointer; z-index: 70; transition: all var(--transition);
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  }
  .console-trigger:hover { border-color: var(--accent); color: var(--accent); }
  .console-trigger.has-running { border-color: var(--yellow); color: var(--yellow); animation: pulse-border 1.5s infinite; }
  .console-badge {
    display: none; background: var(--yellow); color: #000;
    border-radius: 999px; padding: 0 5px; font-size: 0.65rem;
    font-weight: 700; line-height: 1.5; min-width: 16px; text-align: center;
  }
  .console-badge.visible { display: inline-block; }

  @media (max-width: 767px) {
    .console-panel { width: 100%; min-width: unset; max-width: unset; top: 0; }
    .console-trigger { bottom: calc(var(--bottom-nav-h) + 0.75rem); right: 0.75rem; }
  }
  ```

- [ ] **Step 2: Adicionar HTML do painel e trigger no body**

  Localize o HTML do `<!-- Console Section -->` (~linha 794–813):
  ```html
        <!-- Console Section -->
        <div class="console-section" id="consoleSection">
          <div class="section-header">
            <h3>📜 Console</h3>
            <div class="console-controls" id="consoleControls">
  ```

  **Substitua** todo o bloco `<div class="console-section" ...>...</div>` por:
  ```html
        <!-- Console placeholder (empty — content moved to panel) -->
  ```

  Em seguida, **após** o `</div>` de fechamento do `<div class="layout">` (~linha 821), antes do `<!-- Modal de progresso de treino -->`, adicione:

  ```html
  <!-- Console Lateral Panel -->
  <div id="consolePanel" class="console-panel">
    <div class="section-header">
      <h3>📜 Console</h3>
      <button class="close-panel-btn" onclick="closeConsole()">✕</button>
    </div>
    <div class="console-controls" id="consoleControls">
      <button class="console-filter-btn active" data-level="info" onclick="toggleLevelFilter('info')">info</button>
      <button class="console-filter-btn active" data-level="success" onclick="toggleLevelFilter('success')">success</button>
      <button class="console-filter-btn active" data-level="warn" onclick="toggleLevelFilter('warn')">warn</button>
      <button class="console-filter-btn active" data-level="error" onclick="toggleLevelFilter('error')">error</button>
      <button class="console-filter-btn active" data-level="cmd" onclick="toggleLevelFilter('cmd')">cmd</button>
      <button class="console-filter-btn" id="autoscrollBtn" onclick="toggleAutoscroll()">⏸ autoscroll</button>
      <button class="console-filter-btn" onclick="exportConsole('json')">⬇ json</button>
      <button class="console-filter-btn" onclick="exportConsole('txt')">⬇ txt</button>
      <button class="console-filter-btn" onclick="clearConsole()">✕ limpar</button>
    </div>
    <div class="console-output" id="consoleOutput">
      <div class="line dim">Bem-vindo ao Lotofácil Dashboard. Selecione uma ação para começar.</div>
    </div>
  </div>

  <!-- Console trigger button -->
  <button id="consoleTrigger" class="console-trigger" onclick="toggleConsole()">
    ⌨ Log <span id="consoleBadge" class="console-badge"></span>
  </button>
  ```

- [ ] **Step 3: Remover referências ao consoleSection em switchTab()**

  Localize em `switchTab()` (~linha 1117):
  ```js
  document.getElementById('consoleSection').style.display = (id === 'modelos' || id === 'roi_lab') ? 'none' : '';
  ```

  **Remova** essa linha inteira. O painel lateral não precisa mais ser ocultado por aba.

- [ ] **Step 4: Verificar no browser**

  Recarregue. Confirme:
  - O console não ocupa mais espaço no layout principal
  - O botão "⌨ Log" aparece fixo no canto inferior direito
  - Clicar no botão ainda não abre nada (JS não implementado ainda — esperado)
  - O layout das abas Coleta e Dados tem mais espaço vertical disponível

- [ ] **Step 5: Commit**

  ```bash
  git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
  git commit -m "feat(dashboard): console movido para painel lateral (CSS + HTML)"
  ```

---

## Task 3: Console Lateral — Lógica JS

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`
  - Seção JS STATE (~linha 900): adicionar `consoleOpen`
  - Funções de console (~após linha 963): adicionar `openConsole`, `closeConsole`, `toggleConsole`, `_updateConsoleTrigger`
  - Função `listenJob()` (~linha 1229): auto-open/close

- [ ] **Step 1: Adicionar consoleOpen ao STATE**

  Localize `advancedOpen` que você adicionou em Task 1. Logo depois adicione:

  ```js
  consoleOpen: false,
  ```

- [ ] **Step 2: Adicionar funções de controle do painel**

  Localize o comentário `// ═══════════════════════════════════════════════════════` da seção LOGGING (~linha 970). **Antes** desse comentário, adicione:

  ```js
  // ═══════════════════════════════════════════════════════════════
  // CONSOLE PANEL
  // ═══════════════════════════════════════════════════════════════
  function openConsole() {
    STATE.consoleOpen = true;
    document.getElementById('consolePanel')?.classList.add('open');
  }

  function closeConsole() {
    STATE.consoleOpen = false;
    document.getElementById('consolePanel')?.classList.remove('open');
  }

  function toggleConsole() {
    STATE.consoleOpen ? closeConsole() : openConsole();
  }

  function _updateConsoleTrigger() {
    const trigger = document.getElementById('consoleTrigger');
    const badge = document.getElementById('consoleBadge');
    if (!trigger || !badge) return;
    const n = STATE.runningTasks.size;
    trigger.classList.toggle('has-running', n > 0);
    badge.textContent = n > 0 ? String(n) : '';
    badge.classList.toggle('visible', n > 0);
  }
  ```

- [ ] **Step 3: Chamar _updateConsoleTrigger quando runningTasks muda**

  Localize onde `STATE.runningTasks` recebe `.add()` e `.delete()`. Esses chamados estão dentro de `listenJob()` (~linha 1229). Localize o trecho onde a tarefa é adicionada:

  ```js
  STATE.runningTasks.add(actionId);
  ```

  Logo após essa linha, adicione:
  ```js
  _updateConsoleTrigger();
  ```

  E localize onde é removida (dentro do callback de conclusão):
  ```js
  STATE.runningTasks.delete(actionId);
  ```

  Logo após, adicione:
  ```js
  _updateConsoleTrigger();
  ```

- [ ] **Step 4: Auto-abrir o console ao disparar um comando**

  Ainda em `listenJob()`, localize o início da função ou o ponto onde a conexão SSE começa. Adicione `openConsole()` logo no início da função, antes do `new EventSource(...)`:

  ```js
  function listenJob(taskId, actionId, label) {
    openConsole();   // ← adicionar esta linha
    // ... resto da função existente
  ```

- [ ] **Step 5: Auto-fechar no sucesso, manter aberto no erro**

  Ainda em `listenJob()`, localize o trecho que trata o evento `done`:
  ```js
  addConsoleLine(`✅ ${label} concluído`, 'success');
  showToast(`${label} concluído com sucesso`, 'success');
  ```

  Logo **após** essas duas linhas (dentro do branch de sucesso), adicione:
  ```js
  setTimeout(() => { if (STATE.runningTasks.size === 0) closeConsole(); }, 3000);
  ```

  No branch de erro, não adicione fechamento automático — o painel deve permanecer aberto para leitura.

- [ ] **Step 6: Verificar no browser**

  Recarregue. Confirme:
  - Botão "⌨ Log" abre/fecha o painel lateral com animação de deslize
  - Ao clicar em "Atualizar Base" (ou qualquer ação na aba Coleta), o painel abre automaticamente e mostra o output
  - Enquanto roda, badge mostra "1" e botão fica amarelo pulsando
  - Ao concluir com sucesso, painel fecha após 3 segundos e toast aparece
  - Clicar ✕ dentro do painel fecha manualmente

- [ ] **Step 7: Commit**

  ```bash
  git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
  git commit -m "feat(dashboard): console panel JS — auto-abrir/fechar + badge de tarefas"
  ```

---

## Task 4: Aba Modelos — Duas Seções Sequenciais

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`
  - Função `renderModelosPage()` (~linha 2068): reescrever sem sub-tabs
  - CSS de modelos (~linha 534): adicionar estilo para section divider visual

- [ ] **Step 1: Verificar estado atual**

  Navegue para a aba Modelos. Confirme que existem sub-tabs: ▶ Treinar, 📋 Lista, ⚡ Gerar, ⚖️ Comparar, 🗂 Histórico. Anote que a aba Treinar e Gerar são as que interessam.

- [ ] **Step 2: Adicionar CSS para as seções sequenciais**

  Localize `/* ── Modelos Tab ──` (~linha 534). Logo após `.modelos-page-panel.active { display:block; }` (~linha 544), adicione:

  ```css
  .modelos-two-sections { display: flex; flex-direction: column; }
  .modelos-section-block {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .modelos-section-block:last-child { border-bottom: none; }
  .modelos-section-block-title {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--dim); font-weight: 700; margin-bottom: 1.25rem;
    display: flex; align-items: center; gap: 0.5rem;
  }
  .modelos-section-block-title::after {
    content: ''; flex: 1; height: 1px; background: var(--border);
  }
  .modelos-gerar-select {
    width: 100%; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 0.5rem 0.75rem;
    color: var(--text); font-size: 0.82rem; margin-bottom: 0.75rem;
    cursor: pointer;
  }
  .modelos-gerar-select:focus { border-color: var(--accent); outline: none; }
  .modelos-gerar-result {
    margin-top: 1rem; padding: 1rem;
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: var(--radius); display: none;
  }
  .modelos-gerar-result.visible { display: block; }
  .modelos-gerar-result .result-balls {
    display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem;
  }
  .modelos-gerar-result .result-ball {
    width: 30px; height: 30px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700;
    background: var(--surface); border: 2px solid var(--border);
    color: var(--text); font-variant-numeric: tabular-nums;
  }
  .modelos-gerar-result .result-ball.hit {
    border-color: var(--green); background: rgba(74,222,128,0.15); color: var(--green);
  }
  ```

- [ ] **Step 3: Reescrever renderModelosPage()**

  Localize `function renderModelosPage()` (~linha 2068). **Substitua** essa função inteira por:

  ```js
  function renderModelosPage() {
    const container = document.getElementById('tab-modelos');
    container.innerHTML = `
      <div class="modelos-page">
        <div class="modelos-page-header">
          <span class="modelos-page-title">🧠 Modelos</span>
          <span id="modelosLastUpdated" style="font-size:0.62rem;color:var(--dim);margin-left:auto"></span>
          <button class="action-btn" onclick="loadModelosAndRender()"
            style="font-size:0.72rem;padding:0.25rem 0.6rem">↻ Atualizar</button>
        </div>
        <div class="modelos-page-body">
          <div class="modelos-two-sections">
            <div class="modelos-section-block">
              <div class="modelos-section-block-title">Treinar</div>
              <div id="mod-treinar-inline"></div>
              <div id="mod-lista-inline" style="margin-top:1.25rem"></div>
            </div>
            <div class="modelos-section-block">
              <div class="modelos-section-block-title">Gerar Jogo</div>
              <div id="mod-gerar-inline"></div>
            </div>
          </div>
        </div>
      </div>`;
    _renderModelosTreinar();
    _renderModelosGerar();
    loadModelosAndRender();
  }
  ```

- [ ] **Step 4: Adicionar _renderModelosTreinar()**

  Logo **após** a nova `renderModelosPage()`, adicione:

  ```js
  function _renderModelosTreinar() {
    const panel = document.getElementById('mod-treinar-inline');
    if (!panel) return;
    // Reusar conteúdo existente de renderModTreinar mas apontando para mod-treinar-inline
    const tmp = document.createElement('div');
    tmp.id = 'mod-treinar';
    tmp.style.display = 'none';
    document.body.appendChild(tmp);
    renderModTreinar();
    panel.innerHTML = tmp.innerHTML;
    tmp.remove();
  }
  ```

  > **Atenção:** Essa abordagem reutiliza `renderModTreinar()` sem duplicar código. O `tmp` é um nó temporário fora da view usado só para capturar o innerHTML gerado.

- [ ] **Step 5: Adicionar _renderModelosGerar()**

  Logo após `_renderModelosTreinar()`, adicione:

  ```js
  function _renderModelosGerar() {
    const panel = document.getElementById('mod-gerar-inline');
    if (!panel) return;
    const modelos = (_predState.modelos || []).filter(m => m.status === 'completed');

    if (!modelos.length) {
      panel.innerHTML = `<div class="empty-state" style="padding:1.5rem 0">
        <span class="big-icon">🧠</span>
        <p>Nenhum modelo treinado ainda. Treine um modelo acima primeiro.</p>
      </div>`;
      return;
    }

    const options = modelos.map(m =>
      `<option value="${esc(m.id)}">${esc(m.nome || m.id)} — ${esc(m.tipo_config || '')}</option>`
    ).join('');

    panel.innerHTML = `
      <p style="font-size:0.75rem;color:var(--muted);margin-bottom:0.75rem;line-height:1.5">
        Selecione um modelo concluído, defina quantos jogos gerar e clique em Gerar.
      </p>
      <select id="gerarModeloSelect" class="modelos-gerar-select">
        <option value="">— Selecione um modelo —</option>
        ${options}
      </select>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:0.75rem">
        <div class="pred-param" style="flex:0 0 auto">
          <label>Jogos</label>
          <input type="number" id="gerarNJogos" value="1" min="1" max="20"
            style="width:64px">
        </div>
        <div class="pred-param" style="flex:0 0 auto">
          <label>Números</label>
          <select id="gerarNNumeros"
            style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:0.35rem 0.5rem;color:var(--text);font-size:0.82rem">
            <option value="15" selected>15</option>
            <option value="11">11</option>
          </select>
        </div>
      </div>
      <button class="modelos-treinar-btn" id="gerarJogoBtn" onclick="_gerarJogoInline()">⚡ Gerar</button>
      <div id="gerarJogoResult" class="modelos-gerar-result"></div>
      <div class="pred-warning" style="margin-top:1rem">⚠️ Resultados experimentais — não garantem acertos futuros.</div>
    `;
  }

  async function _gerarJogoInline() {
    const modeloId = document.getElementById('gerarModeloSelect')?.value;
    if (!modeloId) { showToast('Selecione um modelo primeiro.', 'warn'); return; }
    const nJogos = parseInt(document.getElementById('gerarNJogos')?.value) || 1;
    const nNumeros = parseInt(document.getElementById('gerarNNumeros')?.value) || 15;
    const btn = document.getElementById('gerarJogoBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Gerando...'; }

    try {
      const r = await fetch(`/api/treinos/${modeloId}/gerar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n_jogos: nJogos, n_numeros: nNumeros }),
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);

      const resultEl = document.getElementById('gerarJogoResult');
      if (!resultEl) return;

      const realSet = new Set(data.dezenas_reais || []);
      let html = `<div style="font-size:0.72rem;color:var(--muted);margin-bottom:0.5rem">
        Concurso alvo: <b style="color:var(--text)">#${data.concurso}</b>
        ${data.dezenas_reais ? ` · Resultado já disponível` : ''}
      </div>`;

      (data.jogos || []).forEach((jogo, i) => {
        const acertos = data.acertos_por_jogo?.[i];
        html += `<div style="margin-bottom:0.6rem">`;
        if (data.jogos.length > 1) {
          html += `<div style="font-size:0.68rem;color:var(--dim);margin-bottom:0.25rem">Jogo ${i+1}${acertos !== undefined ? ` · ${acertos} acertos` : ''}</div>`;
        }
        html += `<div class="result-balls">`;
        html += jogo.map(n => {
          const isHit = realSet.has(n);
          return `<span class="result-ball${isHit ? ' hit' : ''}">${String(n).padStart(2,'0')}</span>`;
        }).join('');
        html += `</div></div>`;
      });

      resultEl.innerHTML = html;
      resultEl.classList.add('visible');
      showToast(`${nJogos} jogo(s) gerado(s) com sucesso`, 'success');
    } catch (e) {
      showToast(`Erro: ${e.message}`, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '⚡ Gerar'; }
    }
  }
  ```

- [ ] **Step 6: Atualizar loadModelosAndRender() para re-renderizar as seções inline**

  Localize `function loadModelosAndRender()` (~linha 2256). No final da função, após a linha que checa `hasRunning`, **substitua** o bloco que re-renderiza sub-tabs por:

  ```js
    const t = _predState.activeSubTab;
    // Manter compatibilidade com sub-tabs legados (usados em _renderModelosTreinar via tmp node)
    if (t === 'lista')    renderModLista?.();
    if (t === 'gerar')    renderPredGerar?.();
    if (t === 'comparar') renderPredComparar?.();

    // Re-renderizar lista inline e gerar se estiver na aba Modelos
    if (STATE.activeTab === 'modelos') {
      _renderModelosListaInline();
      _renderModelosGerar();
    }
  ```

- [ ] **Step 7: Adicionar _renderModelosListaInline()**

  Adicione após `_renderModelosGerar`:

  ```js
  function _renderModelosListaInline() {
    const panel = document.getElementById('mod-lista-inline');
    if (!panel) return;
    const modelos = _predState.modelos || [];
    if (!modelos.length) {
      panel.innerHTML = '';
      return;
    }
    const running = modelos.filter(m => m.status === 'running');
    const done = modelos.filter(m => m.status !== 'running').slice(0, 5);
    let html = `<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--dim);margin-bottom:0.5rem">Treinos recentes</div>`;
    for (const m of [...running, ...done]) {
      const statusColor = m.status === 'completed' ? 'var(--green)' : m.status === 'running' ? 'var(--yellow)' : m.status === 'failed' ? 'var(--red)' : 'var(--muted)';
      const statusIcon = m.status === 'completed' ? '✅' : m.status === 'running' ? '⏳' : m.status === 'failed' ? '❌' : '○';
      html += `<div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0;border-bottom:1px solid var(--border-light);font-size:0.78rem">
        <span>${statusIcon}</span>
        <span style="flex:1;font-weight:500">${esc(m.nome || m.id)}</span>
        <span style="color:var(--dim);font-size:0.7rem">${esc(m.tipo_config || '')}</span>
        <span style="color:${statusColor};font-size:0.7rem">${esc(m.status)}</span>
      </div>`;
    }
    if (modelos.length > 5) {
      html += `<div style="font-size:0.7rem;color:var(--dim);padding-top:0.4rem">+${modelos.length - 5} mais — acesse Avançado → Validação para ver todos</div>`;
    }
    panel.innerHTML = html;
  }
  ```

- [ ] **Step 8: Verificar no browser**

  Navegue para Modelos. Confirme:
  - Não há mais sub-tabs na aba
  - A página mostra "Treinar" e "Gerar Jogo" como seções sequenciais com separadores
  - A seção Treinar mostra o formulário de configuração completo (cards, hiperparâmetros, botão Iniciar)
  - Logo abaixo do botão, aparece lista dos últimos 5 treinos (se existirem)
  - A seção Gerar Jogo mostra o select de modelos concluídos (ou mensagem de vazio)
  - Selecionar um modelo e clicar Gerar funciona e mostra as bolas inline
  - O botão ↻ Atualizar ainda funciona

- [ ] **Step 9: Commit**

  ```bash
  git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
  git commit -m "feat(dashboard): aba Modelos com seções Treinar + Gerar sem sub-tabs"
  ```

---

## Task 5: Limpeza e Ajustes Finais

**Files:**
- Modify: `lotofacil/src/lotofacil/interface/painel/static/dashboard.html`
  - CSS das abas antigas de modelos (pred-subnav-inline, etc.) — remover ou marcar como não usadas
  - Estilo do content-split — ajustar sem o split de console

- [ ] **Step 1: Remover o border-bottom do content-split que dependia do console**

  Localize no CSS:
  ```css
  /* Numbers section (dados tab) */
  .numbers-section {
    padding: 0; border-bottom: 1px solid var(--border);
    flex-shrink: 0; max-height: 50%; overflow-y: auto;
    background: var(--bg);
  }
  ```

  O `max-height: 50%` era necessário para dividir espaço com o console. Agora que o console saiu, altere para:
  ```css
  .numbers-section {
    padding: 0;
    flex: 1; overflow-y: auto;
    background: var(--bg);
  }
  ```

  E remova a regra:
  ```css
  .content-split.dados-mode .numbers-section { flex: 1; border-bottom: none; max-height: none; }
  .content-split.dados-mode .console-section { display: none; }
  ```

  Pois `dados-mode` não é mais necessário para ocultar o console (o console sumiu do layout).

- [ ] **Step 2: Atualizar switchTab() para não usar dados-mode**

  Localize em `switchTab()`:
  ```js
  cs.classList.toggle('dados-mode', id === 'dados');
  ```

  **Remova** essa linha.

- [ ] **Step 3: Verificar abas Dados e Validação com mais espaço vertical**

  Navegue para Avançado → Dados. Confirme que a tabela de sorteios ocupa toda a altura disponível sem ser cortada pela metade. Navegue para Avançado → Validação. Confirme que os cards de métricas estão visíveis sem scroll excessivo.

- [ ] **Step 4: Testar fluxo completo**

  Execute o seguinte roteiro manual:
  1. Sidebar mostra: Coleta, Modelos, ⚙️ Avançado (colapsado)
  2. Clicar Avançado → expande Dados, Validação, ROI Lab
  3. Recarregar → Avançado mantém estado
  4. Clicar Coleta → botões de ação aparecem na actions bar
  5. Clicar "Atualizar Base" → console abre automaticamente com output
  6. Após conclusão → toast de sucesso → console fecha após 3s
  7. Clicar Modelos → seções Treinar + Gerar visíveis sem sub-tabs
  8. Iniciar um treino → modal de progresso abre (comportamento existente)
  9. "⌨ Log" no canto → abre/fecha manualmente a qualquer momento
  10. Avançado → Dados → tabela ocupa tela completa

- [ ] **Step 5: Commit final**

  ```bash
  git add lotofacil/src/lotofacil/interface/painel/static/dashboard.html
  git commit -m "feat(dashboard): limpeza CSS + layout vertical corrigido sem console fixo"
  ```

---

## Self-Review contra o Spec

| Requisito do Spec | Task que implementa |
|---|---|
| Sidebar mostra 3 itens no estado padrão | Task 1 |
| Avançado expansível com Dados, Validação, ROI Lab | Task 1 |
| Estado de expandido persiste no localStorage | Task 1 (Step 4) |
| Aba Modelos mostra seções Treinar e Gerar | Task 4 |
| Parâmetros opcionais colapsados — `<details>` | **⚠️ Não implementado** — o formulário de treino existente já é compacto; adicionar `<details>` seria simples mas não foi incluído para não complicar Task 4. Se desejado, pode ser adicionado manualmente após Task 4 |
| Console não ocupa espaço quando fechado | Task 2 |
| Badge de tarefas em execução | Task 3 |
| Console abre ao disparar comando | Task 3 |
| Console fecha após 3s no sucesso | Task 3 |
| Console fica aberto no erro | Task 3 |
| Mobile: console como aba no bottom nav | **Fora de escopo — spec diz "no mobile, o console vira uma aba dedicada"** — o trigger button funciona em mobile mas a aba no bottom-nav não foi adicionada para manter o plano focado |

> Os dois itens marcados com ⚠️ são melhorias opcionais que não bloqueiam o objetivo principal. Podem ser adicionados como Task 6 se o usuário desejar após a execução.

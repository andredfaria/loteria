# Dataset Relacional — Nexora Sistemas

## Empresa

| Campo | Valor |
|---|---|
| Nome | Nexora Sistemas |
| Segmento | Serviços e Tecnologia |
| Funcionários | 42 |
| Cidades | São Paulo, Campinas, Santo André, Osasco, Barueri |

---

# Funcionários

## u01 — Ana Souza

| Campo | Valor |
|---|---|
| Idade | 29 |
| Cargo | Analista de Produto |
| Skills | produto, UX, pesquisa, comunicação |
| Empresas anteriores | LojaWeb, SoftLab |
| Cidade | São Paulo |
| Transporte | carro |
| Tempo deslocamento | 45 min |
| Gostos | café, organização, trilhas, planejamento |
| Ferramentas | Notion, Figma, Slack, Google Drive |
| Perfil | colaborativa, metódica, observadora |

---

## u02 — Bruno Lima

| Campo | Valor |
|---|---|
| Idade | 34 |
| Cargo | Dev Backend |
| Skills | node, api, postgres, docker |
| Empresas anteriores | FintechX, CodeHouse, Nexora |
| Cidade | Barueri |
| Transporte | carro |
| Tempo deslocamento | 35 min |
| Gostos | música alta, automação, café forte |
| Ferramentas | VS Code, GitHub, Docker, Slack |
| Perfil | direto, técnico, crítico |

---

## u03 — Carla Mendes

| Campo | Valor |
|---|---|
| Idade | 31 |
| Cargo | RH |
| Skills | recrutamento, cultura, mediação |
| Empresas anteriores | PeoplePro, AgroSol |
| Cidade | Santo André |
| Transporte | carro |
| Tempo deslocamento | 55 min |
| Gostos | conversa, eventos internos, rotina |
| Ferramentas | Slack, Calendar, Trello |
| Perfil | empática, paciente, articuladora |

---

## u04 — Diego Rocha

| Campo | Valor |
|---|---|
| Idade | 37 |
| Cargo | Comercial |
| Skills | vendas, negociação, CRM |
| Empresas anteriores | VarejoPro, LeadFlow |
| Cidade | Osasco |
| Transporte | carro |
| Tempo deslocamento | 50 min |
| Gostos | comissão, networking, metas |
| Ferramentas | HubSpot, WhatsApp, Sheets |
| Perfil | persuasivo, competitivo |

---

## u05 — Elisa Prado

| Campo | Valor |
|---|---|
| Idade | 26 |
| Cargo | Data Analyst |
| Skills | sql, power bi, estatística |
| Empresas anteriores | MetricLab |
| Cidade | Campinas |
| Transporte | carro |
| Tempo deslocamento | 70 min |
| Gostos | livros, precisão, silêncio |
| Ferramentas | Power BI, SQL, Excel |
| Perfil | analítica, reservada |

---

## u06 — Felipe Costa

| Campo | Valor |
|---|---|
| Idade | 28 |
| Cargo | Suporte |
| Skills | atendimento, documentação |
| Empresas anteriores | HelpDesk BR |
| Cidade | São Paulo |
| Transporte | carro |
| Tempo deslocamento | 40 min |
| Gostos | jogos, resolver problemas |
| Ferramentas | Zendesk, Slack, WhatsApp |
| Perfil | prestativo, prático |

---

## u07 — Gabriela Nunes

| Campo | Valor |
|---|---|
| Idade | 33 |
| Cargo | Marketing |
| Skills | branding, copy, mídia paga |
| Empresas anteriores | Studio MKT, EcomPlus |
| Cidade | Barueri |
| Transporte | carro |
| Tempo deslocamento | 30 min |
| Gostos | campanhas, design, tendências |
| Ferramentas | Canva, Meta Ads, Notion |
| Perfil | criativa, intuitiva |

---

## u08 — Hugo Ferreira

| Campo | Valor |
|---|---|
| Idade | 41 |
| Cargo | Gestor Operacional |
| Skills | processos, gestão, indicadores |
| Empresas anteriores | LogiMax |
| Cidade | Campinas |
| Transporte | carro |
| Tempo deslocamento | 65 min |
| Gostos | eficiência, controle, previsibilidade |
| Ferramentas | Power BI, ERP, Sheets |
| Perfil | estratégico, exigente |

---

# Relações Internas

| Origem | Destino | Relação | Intensidade | Observação |
|---|---|---|---|---|
| u01 | u07 | works_with | 8 | campanhas e branding |
| u01 | u08 | reports_to | 7 | produto responde à operação |
| u02 | u05 | works_with | 6 | integrações e dados |
| u02 | u06 | helps | 5 | suporte técnico |
| u03 | u06 | works_with | 7 | onboarding |
| u03 | u08 | reports_to | 8 | RH alinhado operação |
| u04 | u07 | works_with | 6 | geração de leads |
| u04 | u08 | conflict | 4 | vendas promete além |
| u05 | u08 | works_with | 7 | indicadores |
| u06 | u03 | friends | 6 | amizade interna |
| u07 | u01 | works_with | 8 | marketing + produto |
| u08 | u02 | mentors | 5 | cobrança técnica |

---

# Dinâmica da Empresa

## Clusters de Moradia

| Região | Usuários |
|---|---|
| Zona Sul | u01, u06 |
| Osasco | u04 |
| Barueri | u02, u07 |
| Campinas | u05, u08 |
| ABC | u03 |

---

## Padrões de Deslocamento

| Tipo | Quantidade | Impacto |
|---|---|---|
| Carro individual | 8 | atraso em horários de pico |
| Carona compartilhada | 2 | maior influência social |

---

## Interesses Compartilhados

- café
- automação
- produtividade
- WhatsApp
- reuniões rápidas

---

## Fricções Internas

- vendas quer velocidade
- operação quer processo
- RH quer previsibilidade
- dados quer rastreabilidade

---

# Cenários para Simulação no MiroFish

## 1. Adoção de IA

**Pergunta:**  
Quem apoia, quem resiste e por quê?

---

## 2. Troca de CRM

**Pergunta:**  
Qual área influencia mais a decisão?

---

## 3. Trabalho Híbrido

**Pergunta:**  
Como deslocamento e cidade afetam aceitação?

---

## 4. Automação de Atendimento

**Pergunta:**  
Quais áreas ganham ou perdem com automação?

---

# Perguntas Avançadas para o MiroFish

- Quem possui maior influência informal?
- Quem tende a criar resistência coletiva?
- Quais grupos possuem afinidade natural?
- Como trânsito afeta humor e produtividade?
- Quem é mais aberto a IA?
- Quem influencia decisões sem cargo de liderança?
- Como gostos pessoais afetam alianças internas?
- Quem seria o primeiro a pedir demissão após mudanças?
- Quais funcionários formariam subgrupos?
- Como um conflito entre vendas e operação se espalharia?
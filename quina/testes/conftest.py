"""Configuração compartilhada da suíte da Quina.

O painel (`quina.interface.painel.server`) falha fechado: sem
`DASHBOARD_PASSWORD` nem `DASHBOARD_PUBLICO=1` ele levanta `SystemExit` já na
importação do módulo, para que nenhum deploy suba sem uma decisão explícita de
segurança. Os testes precisam importar o módulo sem depender dessas variáveis,
então ligamos aqui o escape reservado à suíte.

`setdefault` de propósito: se alguém rodar os testes com a variável já
definida, a escolha de quem chamou prevalece.
"""
import os

os.environ.setdefault("DASHBOARD_SKIP_AUTH_CHECK", "1")

"""
Testes do padrão Observer (não dependem da API do Telegram).

Como rodar, a partir da raiz do projeto:
    python test_observers.py

O script usa um banco SQLite temporário, então não altera o seu financas.db.
"""
import os
import sys
import tempfile
import logging

# Roda em um diretório temporário para não sujar o banco real (data/financas.db)
os.chdir(tempfile.mkdtemp())
logging.basicConfig(level=logging.INFO)

from banco import DBManager
from models import Despesa, Receita
from observers import (
    SujeitoFinanceiro, ObservadorTransacao,
    LogObservador, AlertaOrcamentoObservador, NotificadorMetaObservador,
)

db = DBManager()
USER = 1
ok = 0
falhas = 0


def checa(cond, nome):
    global ok, falhas
    if cond:
        ok += 1
        print(f"PASS: {nome}")
    else:
        falhas += 1
        print(f"FAIL: {nome}")


# --- 1. Mecânica básica: inscrever / notificar / remover ---
class Espiao(ObservadorTransacao):
    def __init__(self):
        self.chamadas = 0

    def atualizar(self, transacao, contexto):
        self.chamadas += 1


sujeito = SujeitoFinanceiro()
espiao = Espiao()
sujeito.adicionar_observador(espiao)
sujeito.adicionar_observador(espiao)  # nao deve duplicar
sujeito.notificar(Receita(10, "teste"), {"usuario_id": USER, "db": db})
checa(espiao.chamadas == 1, "observador notificado uma vez (sem duplicar inscricao)")

sujeito.remover_observador(espiao)
sujeito.notificar(Receita(10, "teste"), {"usuario_id": USER, "db": db})
checa(espiao.chamadas == 1, "observador removido nao recebe mais notificacao")


# --- 2. Um observador com defeito nao derruba os demais ---
class Quebrado(ObservadorTransacao):
    def atualizar(self, transacao, contexto):
        raise RuntimeError("boom")


s2 = SujeitoFinanceiro()
e2 = Espiao()
s2.adicionar_observador(Quebrado())
s2.adicionar_observador(e2)
s2.notificar(Receita(5, "x"), {"usuario_id": USER, "db": db})
checa(e2.chamadas == 1, "falha de um observador nao impede os outros")

# --- 3. AlertaOrcamentoObservador dispara quando estoura o teto ---
db.definir_orcamento("lazer", 100.0, USER)
s3 = SujeitoFinanceiro()
s3.adicionar_observador(LogObservador())
s3.adicionar_observador(AlertaOrcamentoObservador(db))

g1 = Despesa(80, "lazer")
db.salvar_transacao(g1, USER)
ctx = s3.notificar(g1, {"usuario_id": USER, "db": db})
checa(ctx["alertas"] == [], "sem alerta enquanto dentro do orcamento")

g2 = Despesa(50, "lazer")
db.salvar_transacao(g2, USER)
ctx = s3.notificar(g2, {"usuario_id": USER, "db": db})
checa(len(ctx["alertas"]) == 1 and "estourou" in ctx["alertas"][0],
      "alerta de orcamento estourado disparado")

ctx = s3.notificar(Receita(999, "lazer"), {"usuario_id": USER, "db": db})
checa(ctx["alertas"] == [], "receita nao gera alerta de orcamento")

# --- 4. NotificadorMetaObservador comemora meta atingida ---
db.salvar_meta("Viagem", 200.0, USER)
id_meta = db.listar_metas(USER)[0][0]
db.adicionar_poupanca_meta(id_meta, 200.0, USER)
s4 = SujeitoFinanceiro()
s4.adicionar_observador(NotificadorMetaObservador(db))
ctx = s4.notificar(Receita(10, "salario"), {"usuario_id": USER, "db": db})
checa(any("festa" in a or "atingi" in a for a in ctx["alertas"]),
      "notificador de meta comemora meta concluida")

print(f"\nResultado: {ok} passaram, {falhas} falharam")
sys.exit(1 if falhas else 0)

"""
Testes dos padrões Singleton (criacional) e Facade (estrutural).

Como rodar, a partir da raiz do projeto:
    python test_patterns.py

Usa um banco SQLite temporário, então não altera o seu data/financas.db.
"""
import os
import sys
import tempfile
import logging

# Roda em um diretório temporário para não sujar o banco real.
os.chdir(tempfile.mkdtemp())
logging.basicConfig(level=logging.WARNING)

from banco import DBManager
from fachada import FinancasFacade

USER = 42
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


# --- Singleton: DBManager devolve sempre a mesma instância ---
db_a = DBManager()
db_b = DBManager()
checa(db_a is db_b, "DBManager() devolve sempre a mesma instancia (Singleton)")

# Mesmo pedindo outro nome de arquivo, a instancia original e preservada.
db_c = DBManager(db_name="outro.db")
checa(db_c is db_a, "Singleton ignora reinicializacao e mantem a 1a instancia")

# Duas fachadas compartilham o mesmo banco subjacente.
f1 = FinancasFacade()
f2 = FinancasFacade()
checa(f1.db is f2.db, "Fachadas diferentes compartilham o DBManager unico")

# resetar_instancia (uso em testes) realmente cria uma nova instancia depois.
DBManager.resetar_instancia()
db_d = DBManager()
checa(db_d is not db_a, "resetar_instancia permite recriar o Singleton")


# --- Facade: orquestra os subsistemas por tras de uma interface simples ---
fachada = FinancasFacade()

# Registrar uma despesa via fachada: sanitiza, persiste e notifica observers.
msg = fachada.registrar_movimentacao("/gasto", ["R$ 50,00", "Pizza"], USER)
checa("sucesso" in msg.lower(), "registrar_movimentacao devolve confirmacao")

extrato = fachada.obter_extrato(USER)
checa("Pizza" in extrato and "50.00" in extrato, "extrato reflete a despesa registrada")
checa("-50.00" in extrato or "Saldo Atual: R$ -50.00" in extrato,
      "saldo do extrato considera o impacto da despesa")

# Uma receita deve aparecer no extrato com saldo somando.
fachada.registrar_movimentacao("/receita", ["200", "Salario"], USER)
extrato2 = fachada.obter_extrato(USER)
checa("150.00" in extrato2, "saldo combina receita e despesa (200 - 50 = 150)")

# Alerta de orcamento estourado chega atraves da fachada (integra o Observer).
fachada.definir_orcamento(["Pizza", "30"], USER)
msg_alerta = fachada.registrar_movimentacao("/gasto", ["10", "Pizza"], USER)
checa("estourou" in msg_alerta, "fachada propaga alerta de orcamento (Observer integrado)")

# Busca por categoria e por id funcionam pela fachada.
cat = fachada.buscar_categoria("Pizza", USER)
checa("Pizza" in cat, "buscar_categoria devolve transacoes da categoria")

inexistente = fachada.buscar_por_id(999999, USER)
checa("inexistente" in inexistente.lower(), "buscar_por_id trata id inexistente")

# Metas via fachada.
fachada.criar_meta(["1000", "Viagem"], USER)
status_metas = fachada.status_metas(USER)
checa("Viagem" in status_metas, "status_metas lista a meta criada")

# Exportacao devolve um arquivo nao vazio.
arquivo = fachada.exportar_csv(USER)
conteudo = arquivo.getvalue()
checa(len(conteudo) > 0 and b"Categoria" in conteudo, "exportar_csv gera CSV com cabecalho")

print(f"\nResultado: {ok} passaram, {falhas} falharam")
sys.exit(1 if falhas else 0)

"""
Implementação do padrão de projeto Facade (Fachada).

O Facade é um padrão de projeto *estrutural*. Ele oferece uma **interface única
e simplificada** para um conjunto de subsistemas mais complexos, escondendo do
chamador os detalhes de como essas partes se conectam.

O problema que ele resolve aqui
-------------------------------
Para registrar uma simples despesa, o `main.py` precisava conhecer e coordenar
VÁRIOS subsistemas:

    - `SanitizadorMonetario` para limpar o valor digitado;
    - `Despesa` / `Receita` (models) para criar o objeto de domínio;
    - `DBManager` para persistir no banco;
    - `SujeitoFinanceiro` + observadores (Observer) para disparar alertas;
    - `Carteira` / `Orcamento` / `MetaSimples` para formatar extratos e status;
    - `ExportadorCSV` para gerar relatórios.

Isso espalhava regra de negócio pelos handlers do Telegram e deixava o `main.py`
fortemente acoplado a todos esses módulos.

A solução
---------
A `FinancasFacade` concentra toda essa orquestração. O `main.py` passa a
conversar com **um único objeto**: pede "registra essa movimentação", "me dá o
extrato", "exporta os dados" — e recebe de volta o texto pronto (ou o arquivo).
Ele não sabe mais que existe um sanitizador, um banco, um sujeito de observers
etc. Isso reduz o acoplamento e respeita o princípio da Responsabilidade Única:
os handlers cuidam só da conversa com o Telegram; a fachada cuida da lógica.

Importante: o Facade NÃO esconde os subsistemas — eles continuam acessíveis e
podem ser usados diretamente por quem precisar. A fachada apenas oferece o
caminho mais fácil para o caso de uso comum.
"""

from models import Despesa, Receita, Carteira, Orcamento, MetaSimples
from banco import DBManager
from utils import SanitizadorMonetario
from exportador import ExportadorCSV
from observers import (
    SujeitoFinanceiro,
    LogObservador,
    AlertaOrcamentoObservador,
    NotificadorMetaObservador,
)


class FinancasFacade:
    """Fachada que unifica os subsistemas financeiros do PorquinhoBot.

    Cada método público representa um caso de uso completo e devolve o texto
    (em Markdown) pronto para ser enviado ao usuário, ou os dados necessários
    para isso. Toda a coordenação entre banco, observers, sanitizador e
    exportador acontece aqui dentro.
    """

    def __init__(self):
        # DBManager é Singleton: esta chamada devolve a instância única.
        self.db = DBManager()

        # Observer: monta o sujeito e inscreve os observadores uma única vez.
        self.publicador = SujeitoFinanceiro()
        self.publicador.adicionar_observador(LogObservador())
        self.publicador.adicionar_observador(AlertaOrcamentoObservador(self.db))
        self.publicador.adicionar_observador(NotificadorMetaObservador(self.db))

    # ------------------------------------------------------------------
    # Transações
    # ------------------------------------------------------------------
    def registrar_movimentacao(self, comando: str, args: list[str], usuario_id: int) -> str:
        """Sanitiza, cria, persiste a transação e dispara os observadores.

        Devolve a mensagem de sucesso já com eventuais alertas anexados.
        """
        valor = SanitizadorMonetario.limpar_valor(args[0])
        categoria = " ".join(args[1:])

        transacao = Despesa(valor, categoria) if "/gasto" in comando else Receita(valor, categoria)
        self.db.salvar_transacao(transacao, usuario_id)

        # Observer: os observadores podem devolver alertas via contexto.
        contexto = {"usuario_id": usuario_id, "db": self.db}
        self.publicador.notificar(transacao, contexto)

        msg = "🐷 *Oinc oinc!* ✅ Registro efetuado no cofrinho com sucesso!"
        for alerta in contexto.get("alertas", []):
            msg += f"\n\n{alerta}"
        return msg

    def remover_movimentacao(self, id_transacao: int, usuario_id: int) -> str:
        if self.db.remover_transacao(id_transacao, usuario_id):
            return f"🐷 *Oinc oinc!* 🗑️ Registro ID {id_transacao} removido com sucesso!"
        return f"🐷 *Oinc!* ⚠️ Registro ID {id_transacao} não encontrado na sua conta."

    def obter_extrato(self, usuario_id: int) -> str:
        dados = self.db.listar_tudo(usuario_id)
        if not dados:
            return "🐷 *Oinc!* Nenhum registro encontrado. O cofrinho está vazio!"

        msg = "🐷 *Oinc oinc! \nExtrato Geral do Cofrinho:*\n"
        carteira = Carteira()
        for item in dados:
            tipo = "⬆️" if item[5] == "Receita" else "⬇️"
            msg += f"ID: {item[0]} | {tipo} {item[3]}: R$ {item[2]:.2f}\n"
            carteira.adicionar_transacao(self._reconstruir_transacao(item))
        msg += f"\n💰 *Saldo Atual: R$ {carteira.saldo:.2f}*"
        return msg

    def buscar_por_id(self, id_busca: int, usuario_id: int) -> str:
        registro = self.db.buscar_por_id(id_busca, usuario_id)
        if not registro:
            return "🐷 Oinc! ❌ ID inexistente."
        return (
            f"🐷 *Oinc! 🔍 Registro {id_busca}:*\n"
            f"{registro[5]} de R$ {registro[2]:.2f}\n"
            f"Cat: {registro[3]}\nData: {registro[6]}"
        )

    def buscar_categoria(self, categoria: str, usuario_id: int) -> str:
        dados = self.db.listar_por_categoria(categoria, usuario_id)
        return self._montar_mensagem_extrato(dados, f"Categoria: {categoria}")

    def buscar_data(self, mes_ano: str, usuario_id: int) -> str:
        dados = self.db.filtrar_por_data(mes_ano, usuario_id)
        return self._montar_mensagem_extrato(dados, f"Período: {mes_ano}")

    # ------------------------------------------------------------------
    # Exportação
    # ------------------------------------------------------------------
    def exportar_csv(self, usuario_id: int):
        """Devolve um arquivo CSV (BytesIO) pronto para envio no Telegram."""
        dados_brutos = self.db.listar_tudo(usuario_id)
        dados_limpos = [(i[0], i[2], i[3], i[4], i[5], i[6]) for i in dados_brutos]
        return ExportadorCSV.gerar_csv(dados_limpos)

    # ------------------------------------------------------------------
    # Orçamentos
    # ------------------------------------------------------------------
    def definir_orcamento(self, args: list[str], usuario_id: int) -> str:
        categoria = args[0]
        teto = SanitizadorMonetario.limpar_valor(args[1])
        self.db.definir_orcamento(categoria, teto, usuario_id)
        return f"🐷 *Oinc!* 🎯 Teto para {categoria} ok!"

    def status_orcamentos(self, usuario_id: int) -> str:
        msg = "🐷 *Oinc oinc! 📊 Orçamentos:*\n"
        for cat, teto in self.db.listar_orcamentos(usuario_id):
            gastos = self.db.listar_por_categoria(cat, usuario_id)
            total = sum(i[2] for i in gastos if i[5] == "Despesa")
            msg += Orcamento(cat, teto, total).obter_status() + "\n"
        return msg

    # ------------------------------------------------------------------
    # Metas
    # ------------------------------------------------------------------
    def criar_meta(self, args: list[str], usuario_id: int) -> str:
        alvo = SanitizadorMonetario.limpar_valor(args[0])
        nome = " ".join(args[1:])
        self.db.salvar_meta(nome, alvo, usuario_id)
        return f"🐷 *Oinc!* 🎯 Meta '{nome}' criada para o cofrinho!"

    def depositar_meta(self, args: list[str], usuario_id: int) -> str:
        id_meta = int(args[0])
        valor = SanitizadorMonetario.limpar_valor(args[1])
        self.db.adicionar_poupanca_meta(id_meta, valor, usuario_id)
        return f"🐷 *Oinc oinc!* 💸 Depósito na meta {id_meta} devorado!"

    def status_metas(self, usuario_id: int) -> str:
        metas = self.db.listar_metas(usuario_id)
        msg = "🐷 *Oinc oinc! 🎯 Painel de Metas do Cofrinho:*\n\n"
        if not metas:
            msg += "Você ainda não tem nenhuma meta ativa.\n\n"
        else:
            for m in metas:
                obj = MetaSimples(m[1], m[2])
                obj.poupar(m[3])
                msg += f"*(ID: {m[0]})* " + obj.exibir_status() + "\n"
            msg += "\n"
        msg += "📝 *Comandos:*\n"
        msg += "➕ *Criar nova:* `/meta <valor> <Nome>` (Ex: `/meta 1500 Manutencao Gol`)\n"
        msg += "💰 *Guardar dinheiro:* `/poupar <ID> <valor>` (Ex: `/poupar 1 150`)\n"
        return msg

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------
    @staticmethod
    def _reconstruir_transacao(item):
        """Recria um objeto de domínio a partir de uma linha do banco."""
        return Receita(item[2], item[3]) if item[5] == "Receita" else Despesa(item[2], item[3])

    def _montar_mensagem_extrato(self, dados_banco, titulo: str) -> str:
        if not dados_banco:
            return f"🐷 *Oinc!* Nenhum registro encontrado para: {titulo}."
        carteira = Carteira()
        for item in dados_banco:
            carteira.adicionar_transacao(self._reconstruir_transacao(item))
        return f"🐷 *Oinc oinc! 📌 {titulo}*\n" + carteira.get_extrato()

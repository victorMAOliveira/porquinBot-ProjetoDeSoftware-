"""
Implementação do padrão de projeto Observer (Observador).

O Observer define uma dependência um-para-muitos entre objetos, de forma que
quando um objeto (o Sujeito/Subject) muda de estado, todos os seus dependentes
(os Observadores/Observers) são notificados e atualizados automaticamente.

Neste projeto, o evento observado é o registro de uma nova transação no cofrinho.
Cada observador reage a esse evento de forma independente e desacoplada:
    - LogObservador: registra a movimentação no log da aplicação.
    - AlertaOrcamentoObservador: avisa quando uma despesa estoura o orçamento.
    - NotificadorMetaObservador: comemora quando o usuário atinge uma meta.

Para criar um novo comportamento basta escrever uma nova classe que herde de
`ObservadorTransacao` e registrá-la no `SujeitoFinanceiro` — nenhum código
existente precisa ser alterado (princípio Aberto/Fechado).
"""

import logging
from abc import ABC, abstractmethod

from models import Transacao, Despesa


logger = logging.getLogger(__name__)


class ObservadorTransacao(ABC):
    """Interface (contrato) que todo observador de transação deve implementar."""

    @abstractmethod
    def atualizar(self, transacao: Transacao, contexto: dict) -> None:
        """Reage a uma nova transação registrada.

        Args:
            transacao: a transação (Receita ou Despesa) que acabou de ocorrer.
            contexto: dados auxiliares do evento. Convenções usadas:
                - "usuario_id" (int): dono da transação.
                - "db": instância do DBManager, para consultas.
                - "alertas" (list[str]): lista onde o observador pode acrescentar
                  mensagens a serem enviadas de volta ao usuário.
        """
        raise NotImplementedError


class SujeitoFinanceiro:
    """Sujeito (Subject/Observable): mantém e notifica a lista de observadores.

    Não conhece os tipos concretos de observadores — apenas o contrato
    `ObservadorTransacao`. Isso mantém o acoplamento baixo.
    """

    def __init__(self) -> None:
        self._observadores: list[ObservadorTransacao] = []

    def adicionar_observador(self, observador: ObservadorTransacao) -> None:
        """Inscreve um observador (evita duplicatas)."""
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover_observador(self, observador: ObservadorTransacao) -> None:
        """Cancela a inscrição de um observador, se estiver presente."""
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, transacao: Transacao, contexto: dict | None = None) -> dict:
        """Avisa todos os observadores sobre uma nova transação.

        Um observador com defeito não derruba os demais: falhas são logadas
        e o fluxo continua.

        Returns:
            O dicionário de contexto (já preenchido pelos observadores), útil
            para o chamador ler eventuais "alertas".
        """
        contexto = contexto if contexto is not None else {}
        contexto.setdefault("alertas", [])
        for observador in self._observadores:
            try:
                observador.atualizar(transacao, contexto)
            except Exception:  # noqa: BLE001 - um observador não deve quebrar o bot
                logger.exception(
                    "Falha ao notificar o observador %s", type(observador).__name__
                )
        return contexto


# ---------------------------------------------------------------------------
# Observadores concretos
# ---------------------------------------------------------------------------


class LogObservador(ObservadorTransacao):
    """Registra cada movimentação no log da aplicação (auditoria simples)."""

    def atualizar(self, transacao: Transacao, contexto: dict) -> None:
        tipo = type(transacao).__name__
        logger.info(
            "Nova %s | usuario=%s | categoria=%s | valor=R$ %.2f",
            tipo,
            contexto.get("usuario_id"),
            transacao.categoria,
            transacao.valor,
        )


class AlertaOrcamentoObservador(ObservadorTransacao):
    """Avisa quando uma despesa faz a categoria ultrapassar o teto do orçamento."""

    def __init__(self, db) -> None:
        self._db = db

    def atualizar(self, transacao: Transacao, contexto: dict) -> None:
        # Só faz sentido checar orçamento para despesas.
        if not isinstance(transacao, Despesa):
            return

        usuario_id = contexto.get("usuario_id")
        db = contexto.get("db", self._db)
        if usuario_id is None or db is None:
            return

        teto = self._buscar_teto(db, transacao.categoria, usuario_id)
        if teto is None:
            return

        gastos = db.listar_por_categoria(transacao.categoria, usuario_id)
        total_gasto = sum(item[2] for item in gastos if item[5] == "Despesa")

        if total_gasto > teto:
            excedente = total_gasto - teto
            contexto["alertas"].append(
                f"⚠️ *Oinc de alerta!* A categoria *{transacao.categoria}* "
                f"estourou o orçamento em R$ {excedente:.2f} "
                f"(gasto R$ {total_gasto:.2f} de R$ {teto:.2f})."
            )

    @staticmethod
    def _buscar_teto(db, categoria: str, usuario_id: int):
        for cat, teto in db.listar_orcamentos(usuario_id):
            if cat.lower() == categoria.lower():
                return teto
        return None


class NotificadorMetaObservador(ObservadorTransacao):
    """Comemora quando uma receita ajuda a concluir alguma meta do usuário.

    Demonstra como vários observadores independentes reagem ao mesmo evento.
    """

    def __init__(self, db) -> None:
        self._db = db

    def atualizar(self, transacao: Transacao, contexto: dict) -> None:
        if isinstance(transacao, Despesa):
            return

        usuario_id = contexto.get("usuario_id")
        db = contexto.get("db", self._db)
        if usuario_id is None or db is None:
            return

        for meta in db.listar_metas(usuario_id):
            _id, nome, alvo, poupado, _tipo = meta
            if alvo > 0 and poupado >= alvo:
                contexto["alertas"].append(
                    f"🎉 *Oinc de festa!* Você já atingiu a meta *{nome}* "
                    f"(R$ {poupado:.2f} de R$ {alvo:.2f})!"
                )

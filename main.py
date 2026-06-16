import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class PorquinhoBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.db = DBManager()

        # Observer pattern: o bot é o "Sujeito" que notifica observadores
        # sempre que uma transação é registrada. Para adicionar um novo
        # comportamento, basta inscrever outro observador aqui.
        self.publicador = SujeitoFinanceiro()
        self.publicador.adicionar_observador(LogObservador())
        self.publicador.adicionar_observador(AlertaOrcamentoObservador(self.db))
        self.publicador.adicionar_observador(NotificadorMetaObservador(self.db))

    def _obter_teclado_menu(self) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("➕ Nova Receita", callback_data='menu_receita'),
                InlineKeyboardButton("➖ Novo Gasto", callback_data='menu_gasto'),
            ],
            [
                InlineKeyboardButton("📊 Resumo de Saldo", callback_data='menu_extrato'),
                InlineKeyboardButton("📁 Exportar CSV", callback_data='menu_exportar'),
            ],
            [
                InlineKeyboardButton("🚧 Ver Orçamentos", callback_data='menu_orcamento'),
                InlineKeyboardButton("🎯 Minhas Metas", callback_data='menu_metas'),
            ],
            [
                InlineKeyboardButton("🔍 Buscar ID", callback_data='menu_id'),
                InlineKeyboardButton("🏷️ Filtrar Categoria", callback_data='menu_categoria'),
            ],
            [
                InlineKeyboardButton("📅 Histórico", callback_data='menu_data'),
                InlineKeyboardButton("🗑️ Remover Registro", callback_data='menu_remover'),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def exibir_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        texto_menu = "🐷 *Oinc oinc! Bem-vindo ao PorquinhoBot!*\nEscolha a funcionalidade que deseja utilizar:"
        if update.message:
            await update.message.reply_text(texto_menu, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(texto_menu, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")

    async def processar_clique_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'menu_extrato': await self.exibir_extrato(update, context)
        elif query.data == 'menu_exportar': await self.exportar_dados(update, context)
        elif query.data == 'menu_orcamento': await self.ver_status_orcamentos(update, context)
        elif query.data == 'menu_metas': await self.ver_status_metas(update, context)

        elif query.data == 'menu_gasto':
            await query.edit_message_text("🐷 *Oinc oinc! Novo Gasto:*\nDigite: `/gasto <valor> <categoria>`", parse_mode="Markdown")
        elif query.data == 'menu_receita':
            await query.edit_message_text("🐷 *Oinc oinc! Nova Receita:*\nDigite: `/receita <valor> <categoria>`", parse_mode="Markdown")
        elif query.data == 'menu_id':
            await query.edit_message_text("🐷 *Oinc! Consulta de Transação:*\nDigite: `/id <numero>`", parse_mode="Markdown")
        elif query.data == 'menu_categoria':
            await query.edit_message_text("🐷 *Oinc! Listagem por Categoria:*\nDigite: `/categoria <nome>`", parse_mode="Markdown")
        elif query.data == 'menu_data':
            await query.edit_message_text("🐷 *Oinc! Histórico Mês/Ano:*\nDigite: `/data MM/YYYY`", parse_mode="Markdown")
        elif query.data == 'menu_remover':
            await query.edit_message_text("🐷 *Oinc! Remover Registro:*\nDigite: `/remover <ID>`", parse_mode="Markdown")

    async def registrar_movimentacao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            valor = SanitizadorMonetario.limpar_valor(context.args[0])
            categoria = " ".join(context.args[1:])
            comando = update.message.text.split()[0]

            transacao = Despesa(valor, categoria) if "/gasto" in comando else Receita(valor, categoria)
            msg = f"🐷 *Oinc oinc!* ✅ Registro efetuado no cofrinho com sucesso!"

            self.db.salvar_transacao(transacao, user_id)

            # Notifica os observadores sobre a nova transação. Eles podem
            # devolver alertas (ex.: orçamento estourado, meta atingida).
            contexto = {"usuario_id": user_id, "db": self.db}
            self.publicador.notificar(transacao, contexto)
            for alerta in contexto.get("alertas", []):
                msg += f"\n\n{alerta}"

            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* ❌ Deu erro! Use o formato: `/gasto 50 Pizza`", parse_mode="Markdown")

    async def remover_movimentacao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            id_para_remover = int(context.args[0])
            foi_removido = self.db.remover_transacao(id_para_remover, user_id)

            if foi_removido:
                msg = f"🐷 *Oinc oinc!* 🗑️ Registro ID {id_para_remover} removido com sucesso!"
            else:
                msg = f"🐷 *Oinc!* ⚠️ Registro ID {id_para_remover} não encontrado na sua conta."

            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/remover <ID>`", parse_mode="Markdown")

    async def exibir_extrato(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        dados = self.db.listar_tudo(user_id)

        if not dados:
            msg = "🐷 *Oinc!* Nenhum registro encontrado. O cofrinho está vazio!"
        else:
            msg = "🐷 *Oinc oinc! \nExtrato Geral do Cofrinho:*\n"
            carteira_temp = Carteira()

            for item in dados:
                tipo = "⬆️" if item[5] == "Receita" else "⬇️"
                msg += f"ID: {item[0]} | {tipo} {item[3]}: R$ {item[2]:.2f}\n"
                t = Receita(item[2], item[3]) if item[5] == "Receita" else Despesa(item[2], item[3])
                carteira_temp.adicionar_transacao(t)

            msg += f"\n💰 *Saldo Atual: R$ {carteira_temp.saldo:.2f}*"

        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")

    async def buscar_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            id_busca = int(context.args[0])
            registro = self.db.buscar_por_id(id_busca, user_id)
            msg = f"🐷 *Oinc! 🔍 Registro {id_busca}:*\n{registro[5]} de R$ {registro[2]:.2f}\nCat: {registro[3]}\nData: {registro[6]}" if registro else "🐷 Oinc! ❌ ID inexistente."
            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/id <numero>`", parse_mode="Markdown")

    def _montar_mensagem_extrato(self, dados_banco, titulo: str) -> str:
        if not dados_banco:
            return f"🐷 *Oinc!* Nenhum registro encontrado para: {titulo}."
        carteira_temp = Carteira()
        for item in dados_banco:
            t = Receita(item[2], item[3]) if item[5] == "Receita" else Despesa(item[2], item[3])
            carteira_temp.adicionar_transacao(t)
        return f"🐷 *Oinc oinc! 📌 {titulo}*\n" + carteira_temp.get_extrato()

    async def buscar_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            cat = " ".join(context.args)
            dados = self.db.listar_por_categoria(cat, user_id)
            msg = self._montar_mensagem_extrato(dados, f"Categoria: {cat}")
            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/categoria <nome>`", parse_mode="Markdown")

    async def buscar_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            dt = context.args[0]
            dados = self.db.filtrar_por_data(dt, user_id)
            msg = self._montar_mensagem_extrato(dados, f"Período: {dt}")
            await update.message.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/data MM/YYYY`", parse_mode="Markdown")

    async def exportar_dados(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        base = update.message if update.message else update.callback_query.message
        status = await base.reply_text("🐷 *Oinc oinc!* ⏳ Cavando seus dados...")
        try:
            dados_brutos = self.db.listar_tudo(user_id)
            dados_limpos = [(i[0], i[2], i[3], i[4], i[5], i[6]) for i in dados_brutos]
            file = ExportadorCSV.gerar_csv(dados_limpos)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename="relatorio_porquinho.csv", caption="🐷 Oinc! Aqui está a sua papelada!", reply_markup=self._obter_teclado_menu())
            await status.delete()
        except:
            await status.edit_text("🐷 *Oinc!* ❌ Erro na exportação.", reply_markup=self._obter_teclado_menu())

    async def definir_orcamento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            cat = context.args[0]
            teto = SanitizadorMonetario.limpar_valor(context.args[1])
            self.db.definir_orcamento(cat, teto, user_id)
            await update.message.reply_text(f"🐷 *Oinc!* 🎯 Teto para {cat} ok!", reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/orcamento <cat> <valor>`", parse_mode="Markdown")

    async def ver_status_orcamentos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        base = self.db.listar_orcamentos(user_id)
        msg = "🐷 *Oinc oinc! 📊 Orçamentos:*\n"
        for cat, teto in base:
            gastos = self.db.listar_por_categoria(cat, user_id)
            total = sum([i[2] for i in gastos if i[5] == "Despesa"])
            msg += Orcamento(cat, teto, total).obter_status() + "\n"

        target = update.callback_query if update.callback_query else update.message
        if update.callback_query: await target.edit_message_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        else: await target.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")

    async def criar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            alvo = SanitizadorMonetario.limpar_valor(context.args[0])
            nome = " ".join(context.args[1:])
            self.db.salvar_meta(nome, alvo, user_id)
            await update.message.reply_text(f"🐷 *Oinc!* 🎯 Meta '{nome}' criada para o cofrinho!", reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/meta <valor> <nome>`", parse_mode="Markdown")

    async def depositar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            id_m = int(context.args[0])
            val = SanitizadorMonetario.limpar_valor(context.args[1])
            self.db.adicionar_poupanca_meta(id_m, val, user_id)
            await update.message.reply_text(f"🐷 *Oinc oinc!* 💸 Depósito na meta {id_m} devorado!", reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/poupar <ID> <valor>`", parse_mode="Markdown")

    async def ver_status_metas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        metas = self.db.listar_metas(user_id)

        msg = "🐷 *Oinc oinc! 🎯 Painel de Metas do Cofrinho:*\n\n"
        if not metas:
            msg += "Você ainda não tem nenhuma meta ativa.\n\n"
        else:
            for m in metas:
                obj = MetaSimples(m[1], m[2])
                obj.poupar(m[3])
                msg += f"*(ID: {m[0]})* " + obj.exibir_status() + "\n"
            msg += "\n"

        msg += "📝 *Comandos Interativos:*\n"
        msg += "➕ *Criar nova:* `/meta <valor> <Nome>` (Ex: `/meta 1500 Manutencao Gol`)\n"
        msg += "💰 *Guardar dinheiro:* `/poupar <ID> <valor>` (Ex: `/poupar 1 150`)\n"

        target = update.callback_query if update.callback_query else update.message
        if update.callback_query: await target.edit_message_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")
        else: await target.reply_text(msg, reply_markup=self._obter_teclado_menu(), parse_mode="Markdown")

    def run(self):
        app = ApplicationBuilder().token(self.token).build()

        app.add_handler(CommandHandler("start", self.exibir_menu))
        app.add_handler(CommandHandler("menu", self.exibir_menu))
        app.add_handler(CommandHandler("gasto", self.registrar_movimentacao))
        app.add_handler(CommandHandler("receita", self.registrar_movimentacao))
        app.add_handler(CommandHandler("remover", self.remover_movimentacao))
        app.add_handler(CommandHandler("extrato", self.exibir_extrato))
        app.add_handler(CommandHandler("id", self.buscar_id))
        app.add_handler(CommandHandler("categoria", self.buscar_categoria))
        app.add_handler(CommandHandler("data", self.buscar_data))
        app.add_handler(CommandHandler("exportar", self.exportar_dados))
        app.add_handler(CommandHandler("orcamento", self.definir_orcamento))
        app.add_handler(CommandHandler("status", self.ver_status_orcamentos))
        app.add_handler(CommandHandler("meta", self.criar_meta))
        app.add_handler(CommandHandler("poupar", self.depositar_meta))
        app.add_handler(CommandHandler("status_metas", self.ver_status_metas))
        app.add_handler(CallbackQueryHandler(self.processar_clique_menu))

        print("🐷 PorquinhoBot Online e fazendo Oinc Oinc!")
        app.run_polling()

if __name__ == "__main__":
    bot = PorquinhoBot()
    bot.run()

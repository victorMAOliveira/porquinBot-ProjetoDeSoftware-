import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from fachada import FinancasFacade

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Texto único com a lista de comandos disponíveis (substitui o menu de botões).
TEXTO_MENU = (
    "🐷 *Oinc oinc! Bem-vindo ao PorquinhoBot!*\n"
    "Use os comandos abaixo:\n\n"
    "💸 `/gasto <valor> <categoria>` - registra um gasto (ex: `/gasto 50 Pizza`)\n"
    "💰 `/receita <valor> <categoria>` - registra uma entrada (ex: `/receita 5000 Salario`)\n"
    "📊 `/extrato` - mostra o extrato e o saldo atual\n"
    "🔍 `/id <numero>` - consulta uma transação pelo ID\n"
    "🏷️ `/categoria <nome>` - lista transações de uma categoria\n"
    "📅 `/data MM/YYYY` - histórico de um mês/ano\n"
    "🗑️ `/remover <ID>` - remove um registro\n"
    "📁 `/exportar` - gera um CSV com seus dados\n\n"
    "🚧 `/orcamento <cat> <valor>` - define um teto de gastos\n"
    "📊 `/status` - mostra a situação dos orçamentos\n\n"
    "🎯 `/meta <valor> <Nome>` - cria uma meta (ex: `/meta 1500 Viagem`)\n"
    "💵 `/poupar <ID> <valor>` - guarda dinheiro numa meta\n"
    "🐷 `/status_metas` - mostra o painel de metas"
)


class PorquinhoBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_TOKEN")

        # Facade pattern: o bot conversa apenas com a fachada. Toda a
        # orquestração (banco Singleton, observers, sanitizador, exportador)
        # vive em FinancasFacade, mantendo os handlers enxutos e desacoplados.
        self.financas = FinancasFacade()

    async def exibir_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(TEXTO_MENU, parse_mode="Markdown")

    async def registrar_movimentacao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            comando = update.message.text.split()[0]
            msg = self.financas.registrar_movimentacao(comando, context.args, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* ❌ Deu erro! Use o formato: `/gasto 50 Pizza`", parse_mode="Markdown")

    async def remover_movimentacao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            id_para_remover = int(context.args[0])
            msg = self.financas.remover_movimentacao(id_para_remover, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/remover <ID>`", parse_mode="Markdown")

    async def exibir_extrato(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = self.financas.obter_extrato(update.effective_user.id)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def buscar_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            id_busca = int(context.args[0])
            msg = self.financas.buscar_por_id(id_busca, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/id <numero>`", parse_mode="Markdown")

    async def buscar_categoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            cat = " ".join(context.args)
            msg = self.financas.buscar_categoria(cat, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/categoria <nome>`", parse_mode="Markdown")

    async def buscar_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            dt = context.args[0]
            msg = self.financas.buscar_data(dt, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/data MM/YYYY`", parse_mode="Markdown")

    async def exportar_dados(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = await update.message.reply_text("🐷 *Oinc oinc!* ⏳ Cavando seus dados...")
        try:
            file = self.financas.exportar_csv(update.effective_user.id)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename="relatorio_porquinho.csv", caption="🐷 Oinc! Aqui está a sua papelada!")
            await status.delete()
        except:
            await status.edit_text("🐷 *Oinc!* ❌ Erro na exportação.")

    async def definir_orcamento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            msg = self.financas.definir_orcamento(context.args, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/orcamento <cat> <valor>`", parse_mode="Markdown")

    async def ver_status_orcamentos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = self.financas.status_orcamentos(update.effective_user.id)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def criar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            msg = self.financas.criar_meta(context.args, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/meta <valor> <nome>`", parse_mode="Markdown")

    async def depositar_meta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            msg = self.financas.depositar_meta(context.args, update.effective_user.id)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("🐷 *Oinc!* Uso: `/poupar <ID> <valor>`", parse_mode="Markdown")

    async def ver_status_metas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = self.financas.status_metas(update.effective_user.id)
        await update.message.reply_text(msg, parse_mode="Markdown")

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

        print("🐷 PorquinhoBot Online e fazendo Oinc Oinc!")
        app.run_polling()

if __name__ == "__main__":
    bot = PorquinhoBot()
    bot.run()

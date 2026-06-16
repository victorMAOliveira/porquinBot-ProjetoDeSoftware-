# 🐷 PorquinhoBot - Gerenciador Financeiro Pessoal no Telegram

O **PorquinhoBot** é um bot interativo para o Telegram desenvolvido em Python. Ele atua como seu assistente financeiro pessoal, ajudando a registrar despesas, ganhos, acompanhar metas financeiras e exportar relatórios diretamente pelo chat.

Este projeto foi desenvolvido aplicando conceitos de **Programação Orientada a Objetos (POO)**, incluindo Herança, Classes Abstratas e Polimorfismo.

---

## ✨ Funcionalidades Implementadas

O bot foi construído de forma modular e conta com as seguintes funcionalidades:

* **💰 Registro de Transações:** Adicione rapidamente receitas e despesas informando o valor e a descrição.
* **🎯 Gestão de Metas (Polimorfismo):** 
  * Crie *Metas Simples* (baseadas em porcentagem de economia).
  * Crie *Metas com Prazo* (acompanhamento de dias restantes).
* **📊 Consulta de Saldo e Extrato:** Veja o resumo da sua carteira em tempo real.
* **💾 Persistência de Dados:** Uso de banco de dados SQLite (`financas.db`) para garantir que seus dados não sejam perdidos ao reiniciar o bot.
* **📑 Exportação de Relatórios:** Geração de arquivos com o histórico de transações via módulo exportador.

---

## 📂 Arquitetura do Projeto

A estrutura de arquivos foi pensada para separar as responsabilidades do código:

* `main.py`: Ponto de entrada do bot, gerencia a interface com a API do Telegram e os comandos do usuário.
* `models.py`: Contém as regras de negócio e as classes do domínio (`Transacao`, `Despesa`, `Receita`, `Meta`, `Carteira`).
* `banco.py`: Classe `DBManager` responsável pela comunicação e queries no SQLite.
* `observers.py`: Implementação do **Observer pattern** (sujeito e observadores de transações).
* `exportador.py`: Lógica para formatar e exportar os dados do usuário.
* `utils.py`: Funções auxiliares e de formatação.
* `requirements.txt`: Lista de dependências do projeto.
* `data/financas.db`: Arquivo local do banco de dados (gerado automaticamente).

---

## 🔔 Observer Pattern (Padrão Observador)

Além de POO, o projeto aplica o **Observer**, um padrão de projeto comportamental. Ele cria uma relação *um-para-muitos*: quando um evento acontece no **Sujeito** (Subject), todos os **Observadores** (Observers) inscritos são notificados e reagem de forma automática e independente.

No PorquinhoBot, o evento observado é o **registro de uma nova transação**. Toda a lógica vive em `observers.py`:

* `ObservadorTransacao` — a interface (classe abstrata) que todo observador implementa, com o método `atualizar(transacao, contexto)`.
* `SujeitoFinanceiro` — o sujeito, que mantém a lista de observadores (`adicionar_observador`, `remover_observador`) e dispara as notificações (`notificar`).
* Observadores concretos, cada um com uma responsabilidade única:
  * `LogObservador` — registra a movimentação no log (auditoria).
  * `AlertaOrcamentoObservador` — avisa quando uma despesa estoura o teto do orçamento.
  * `NotificadorMetaObservador` — comemora quando uma meta é atingida.

**Por que isso segue boas práticas?** O `main.py` apenas dispara `notificar(...)` e não sabe *quem* vai reagir nem *como*. Isso mantém o **baixo acoplamento** e respeita o **princípio Aberto/Fechado**: para adicionar um novo comportamento (ex.: enviar e-mail, atualizar um dashboard), você cria uma nova classe e a inscreve — sem alterar o código existente. Um observador que falhar é isolado (a falha é logada) e não derruba os demais nem o bot.

### Como usar no código

```python
from observers import SujeitoFinanceiro, LogObservador, AlertaOrcamentoObservador
from models import Despesa

# 1. Crie o sujeito e inscreva os observadores desejados
publicador = SujeitoFinanceiro()
publicador.adicionar_observador(LogObservador())
publicador.adicionar_observador(AlertaOrcamentoObservador(db))

# 2. Ao registrar uma transação, notifique os observadores
transacao = Despesa(50, "lazer")
db.salvar_transacao(transacao, usuario_id)

contexto = {"usuario_id": usuario_id, "db": db}
publicador.notificar(transacao, contexto)

# 3. Leia eventuais alertas devolvidos pelos observadores
for alerta in contexto["alertas"]:
    print(alerta)  # ex.: enviar de volta ao usuário no Telegram
```

No bot, essa integração já está pronta: o `PorquinhoBot` cria o `publicador` no construtor e chama `notificar(...)` dentro de `registrar_movimentacao`, anexando os alertas à resposta enviada ao usuário.

### Como criar um novo observador

Basta herdar de `ObservadorTransacao`, implementar `atualizar` e inscrevê-lo:

```python
from observers import ObservadorTransacao

class MeuObservador(ObservadorTransacao):
    def atualizar(self, transacao, contexto):
        # sua lógica aqui (ex.: somar pontos, enviar webhook...)
        contexto["alertas"].append("🐷 Algo aconteceu!")

# em main.py, dentro de __init__:
self.publicador.adicionar_observador(MeuObservador())
```

Nenhum outro arquivo precisa ser modificado.

---

## 🚀 Como Utilizar (Passo a Passo)

### 1. Pré-requisitos
Certifique-se de ter o **Python 3.10+** instalado em sua máquina. Você também precisará criar um bot no Telegram através do [BotFather](https://t.me/botfather) para obter o seu `TOKEN`.

### 2. Clonando o Repositório
Abra o seu terminal e execute:
```bash
git clone https://github.com/SEU_USUARIO/porquinBot-ProjetoDeSoftware.git
cd porquinBot-ProjetoDeSoftware
```

### 3. Criando o Ambiente Virtual e Instalando Dependências
É uma boa prática rodar o projeto em um ambiente virtual isolado:

```bash
# Criar o ambiente virtual
python -m venv .venv

# Ativar o ambiente (Windows)
.\.venv\Scripts\activate

# Ativar o ambiente (Linux/Mac)
source .venv/bin/activate

# Instalar as bibliotecas necessárias
pip install -r requirements.txt
```

### 4. Configurando as Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto e adicione o token do seu bot:

```env
TELEGRAM_TOKEN=cole_seu_token_aqui_sem_aspas
```

### 5. Executando o Bot
Com tudo configurado, basta rodar o arquivo principal:

```bash
python main.py
```

Se tudo der certo, você verá a mensagem:

```
🐷 PorquinhoBot Online e fazendo Oinc Oinc!
```

---

## 📱 Comandos do Bot no Telegram

Inicie uma conversa com o seu bot no Telegram e use os seguintes comandos:

* `/start` ou `/menu` - Exibe o menu principal de opções.
* `/receita <valor> <descrição>` - Registra uma entrada de dinheiro  
  (ex: `/receita 5000 Salário`).
* `/despesa <valor> <descrição>` - Registra uma saída de dinheiro  
  (ex: `/despesa 50 Pizza`).
* `/saldo` - Mostra o saldo atual e o resumo de entradas e saídas.
* `/extrato` - Exibe as últimas transações registradas.
* `/metas` - Menu para visualização e criação de metas financeiras.
* `/exportar` - Gera um arquivo com todos os seus dados e envia no chat.

---

## 📌 Observações

Projeto desenvolvido para a disciplina de Projeto de Software.

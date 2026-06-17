import sqlite3
import os
from models import Despesa, Receita
from singleton import SingletonMeta

class DBManager(metaclass=SingletonMeta):
    """Gerenciador único (Singleton) de acesso ao banco SQLite.

    Graças à metaclasse ``SingletonMeta``, qualquer ``DBManager()`` ao longo do
    código devolve sempre a MESMA instância. O construtor roda uma única vez,
    então as tabelas são inicializadas apenas na primeira chamada.
    """

    def __init__(self, db_name="financas.db"):
        if not os.path.exists('data'):
            os.makedirs('data')
        self._db_path = os.path.join('data', db_name)
        self._inicializar_banco()

    def _conectar(self):
        return sqlite3.connect(self._db_path)

    def _inicializar_banco(self):
        conn = self._conectar()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS transacoes 
                          (id INTEGER PRIMARY KEY, usuario_id INTEGER, valor REAL, categoria TEXT, descricao TEXT, tipo TEXT, data TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS orcamentos 
                          (usuario_id INTEGER, categoria TEXT, teto REAL, PRIMARY KEY (usuario_id, categoria))''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS metas 
                          (id INTEGER PRIMARY KEY, usuario_id INTEGER, nome TEXT, alvo REAL, poupado REAL, tipo TEXT)''')
        
        conn.commit()
        conn.close()

    def salvar_transacao(self, t, usuario_id: int):
        tipo = "Receita" if isinstance(t, Receita) else "Despesa"
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO transacoes (usuario_id, valor, categoria, descricao, tipo, data)
                          VALUES (?, ?, ?, ?, ?, ?)''', 
                       (usuario_id, t.valor, t.categoria, t._descricao, tipo, t.data_formatada))
        conn.commit()
        conn.close()

    def remover_transacao(self, id_transacao: int, usuario_id: int) -> bool:
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transacoes WHERE id = ? AND usuario_id = ?', (id_transacao, usuario_id))
        sucesso = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return sucesso

    def listar_tudo(self, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transacoes WHERE usuario_id = ? ORDER BY id DESC', (usuario_id,))
        dados = cursor.fetchall()
        conn.close()
        return dados

    def buscar_por_id(self, id_transacao: int, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transacoes WHERE id = ? AND usuario_id = ?', (id_transacao, usuario_id))
        dado = cursor.fetchone()
        conn.close()
        return dado

    def listar_por_categoria(self, categoria: str, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transacoes WHERE LOWER(categoria) = LOWER(?) AND usuario_id = ?', (categoria, usuario_id))
        dados = cursor.fetchall()
        conn.close()
        return dados

    def filtrar_por_data(self, mes_ano: str, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transacoes WHERE data LIKE ? AND usuario_id = ? ORDER BY id DESC', (f'%{mes_ano}%', usuario_id))
        dados = cursor.fetchall()
        conn.close()
        return dados

    def definir_orcamento(self, categoria: str, teto: float, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO orcamentos (usuario_id, categoria, teto) VALUES (?, ?, ?)', (usuario_id, categoria, teto))
        conn.commit()
        conn.close()

    def listar_orcamentos(self, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT categoria, teto FROM orcamentos WHERE usuario_id = ?', (usuario_id,))
        dados = cursor.fetchall()
        conn.close()
        return dados

    def salvar_meta(self, nome: str, alvo: float, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO metas (usuario_id, nome, alvo, poupado, tipo) VALUES (?, ?, ?, ?, ?)', 
                       (usuario_id, nome, alvo, 0.0, 'Simples'))
        conn.commit()
        conn.close()

    def adicionar_poupanca_meta(self, id_meta: int, valor: float, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('UPDATE metas SET poupado = poupado + ? WHERE id = ? AND usuario_id = ?', (valor, id_meta, usuario_id))
        conn.commit()
        conn.close()

    def listar_metas(self, usuario_id: int):
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, alvo, poupado, tipo FROM metas WHERE usuario_id = ?', (usuario_id,))
        dados = cursor.fetchall()
        conn.close()
        return dados
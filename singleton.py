"""
Implementação do padrão de projeto Singleton (Instância Única).

O Singleton é um padrão de projeto *criacional*. Ele garante que uma classe
tenha **apenas uma instância** durante toda a execução do programa e fornece um
**ponto de acesso global** a essa instância.

Neste projeto o Singleton é aplicado ao `DBManager` (ver `banco.py`). Faz sentido
existir apenas um gerenciador do banco de dados: ele centraliza o caminho do
arquivo SQLite, a inicialização das tabelas e todas as consultas. Se cada parte
do código criasse o seu próprio `DBManager`, teríamos várias inicializações
desnecessárias e o risco de configurações divergentes apontando para arquivos
diferentes.

Como funciona aqui
------------------
Usamos uma **metaclasse** (`SingletonMeta`). A metaclasse controla o que acontece
quando a classe é "chamada" para criar um objeto (ou seja, `DBManager()`):

    - Na primeira chamada, o objeto é criado normalmente e guardado num cache.
    - Nas chamadas seguintes, o mesmo objeto guardado é devolvido — o
      construtor (`__init__`) NÃO roda de novo.

A vantagem da metaclasse sobre sobrescrever `__new__` é que o `__init__` da
classe alvo não precisa de nenhuma gambiarra para "lembrar" se já foi
inicializado: a metaclasse cuida disso de forma transparente e reaproveitável
por qualquer classe que queira ser Singleton.
"""

import threading


class SingletonMeta(type):
    """Metaclasse que transforma qualquer classe em um Singleton.

    Basta declarar ``class MinhaClasse(metaclass=SingletonMeta): ...`` e todas
    as instanciações ``MinhaClasse()`` passarão a devolver o mesmo objeto.

    É seguro para uso com múltiplas threads: a criação da primeira instância é
    protegida por um lock para evitar que duas threads criem instâncias
    diferentes simultaneamente.
    """

    # Cache de instâncias, uma por classe que usa esta metaclasse.
    _instancias: dict[type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Verificação dupla (double-checked locking): primeiro sem o lock, por
        # desempenho; e, se necessário, de novo dentro do lock, por segurança.
        if cls not in cls._instancias:
            with cls._lock:
                if cls not in cls._instancias:
                    cls._instancias[cls] = super().__call__(*args, **kwargs)
        return cls._instancias[cls]

    def resetar_instancia(cls) -> None:
        """Descarta a instância em cache desta classe.

        Útil principalmente em testes, onde queremos um estado limpo entre
        cenários. Não deve ser usado no fluxo normal da aplicação.
        """
        cls._instancias.pop(cls, None)

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from MensagemLog import MensagemLog

class CarregamentoSetup:

    _instance = None

    aplicacao_carregamento = "Loading"

    ### PONTOS DE ACESSO DESTINO ###

    conn_params_staging = {
        'dbname': 'juniordbdestino'
        , 'user': 'dbadmin'
        , 'password': 'dbadmin123'
        , 'host': 'juniordbdestino'
        , 'port': '5432'
    }

    string_de_conexao_postgres_destino = (
        f"postgresql://{conn_params_staging['user']}:{conn_params_staging['password']}@{conn_params_staging['host']}:{conn_params_staging['port']}/{conn_params_staging['dbname']}"
    )

    MensagemLog.exibir_mensagem("INFO", "Criando conexão com o banco de dados Destino")

    conector_postgres_destino = create_engine(string_de_conexao_postgres_destino)

    contagem_registros = None

    try:
        
        MensagemLog.exibir_mensagem("INFO", "Consultando tabela de processamentos")

        with conector_postgres_destino.connect() as conexao:
            resultado = conexao.execute(text("SELECT COUNT(*) FROM staging.controle_procm WHERE nome_aplic = 'Loading'"))
            contagem_registros = resultado.scalar()

    except Exception as e:
        
        MensagemLog.exibir_mensagem("INFO", f"Erro ao conectar ao banco de dados: {e}")

    MensagemLog.exibir_mensagem("INFO", "Parametrizando Data de Inicio da Extração")

    if contagem_registros is None:

        data_inicio_extracao_dados = "2017-01-01"

    elif contagem_registros == 0:

        data_inicio_extracao_dados = "2017-01-01"

    else:

        data_inicio_extracao_dados = (
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") # Conforme necessidade, o timedelta pode ser mudado
        )

    MensagemLog.exibir_mensagem("INFO", f"Configurações listadas com sucesso. Data Inicio Extração {data_inicio_extracao_dados}")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

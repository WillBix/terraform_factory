import pandas as pd
import traceback

from datetime import datetime
from sqlalchemy import Table, MetaData
from sqlalchemy.dialects.postgresql import insert

from MensagemLog import MensagemLog
from CarregamentoSetup import CarregamentoSetup


class CarregamentoServico:

    def __init__(self, data_inicio_processamento: str) -> None:

        self.data_inicio_processamento = data_inicio_processamento

    @staticmethod
    def obter_dados_vendas_staging(data_inicio_processamento: str) -> pd.DataFrame:

        consulta_tabela_staging_vendas = (
            """
            SELECT
                id_venda
                , id_funcionario
                , id_Categoria
                , data_venda
                , venda  
            FROM staging.vendas_stg WHERE data_venda >= %s
            """
        )

        df_dados_vendas_postgres = pd.read_sql_query(
            consulta_tabela_staging_vendas
            , con = CarregamentoSetup.conector_postgres_destino
            , params = (data_inicio_processamento, )
        )

        return df_dados_vendas_postgres

    @staticmethod
    def obter_dados_funcionarios_staging() -> pd.DataFrame:

        consulta_tabela_staging_funcionario = (
            """
            SELECT id_funcionario, nome_funcionario
            FROM staging.funcionarios_stg
            """
        )

        df_dados_funcionarios_postgres = pd.read_sql_query(
            consulta_tabela_staging_funcionario
            , con = CarregamentoSetup.conector_postgres_destino
        )

        return df_dados_funcionarios_postgres

    @staticmethod
    def obter_dados_categorias_staging() -> pd.DataFrame:

        consulta_tabela_staging_categorias = (
            """
            SELECT id_categoria, nome_categoria
            FROM staging.categorias_stg
            """
        )

        df_dados_categorias_postgres = pd.read_sql_query(
            consulta_tabela_staging_categorias
            , con = CarregamentoSetup.conector_postgres_destino
        )

        return df_dados_categorias_postgres

    @staticmethod
    def cria_dataframe_fato(df_vendas: pd.DataFrame, df_funcionarios: pd.DataFrame, df_categorias: pd.DataFrame) -> pd.DataFrame:

        chaves_relacionamento_vendas_funcionario = 'id_funcionario'
        chaves_relacionamento_vendas_categorias = 'id_categoria'
        forma_relacionamento_tabelas = 'many_to_one'

        df_fato_vendas_destino = pd.merge(
            df_vendas
            , df_funcionarios
            , how = 'left'
            , left_on = chaves_relacionamento_vendas_funcionario
            , right_on = chaves_relacionamento_vendas_funcionario
            , validate = forma_relacionamento_tabelas
        )
    
        df_fato_vendas_destino = pd.merge(
            df_fato_vendas_destino
            , df_categorias
            , how = 'left'
            , left_on = chaves_relacionamento_vendas_categorias
            , right_on = chaves_relacionamento_vendas_categorias
            , validate = forma_relacionamento_tabelas
        )

        df_fato_vendas_destino['data_procm'] = datetime.now()

        return df_fato_vendas_destino

    @staticmethod
    def persistir_dados_tabela_destino_postgres(df_fato_vendas_destino: pd.DataFrame, nome_tabela_postgres_destino: str) -> None:
        
        MensagemLog.exibir_mensagem("INFO", "Realizando conexão com tabela destino")
        
        metadados_banco_destino = MetaData(bind = CarregamentoSetup.conector_postgres_destino)
        
        MensagemLog.exibir_mensagem("INFO", "Abrindo conexão da tabela destino")

        tabela_postgres_destino = Table(
            nome_tabela_postgres_destino
            , metadados_banco_destino
            , autoload_with = CarregamentoSetup.conector_postgres_destino
            , schema = 'destino'
        )

        registros_dataframe_gravacao = df_fato_vendas_destino.to_dict(orient = 'records')
        
        MensagemLog.exibir_mensagem("INFO", "Configurando o comando de insert")

        configuracao_insert = insert(tabela_postgres_destino).values(registros_dataframe_gravacao)

        colunas_para_verificacao_insert = [
            'id_venda'
            , 'id_funcionario'
            , 'id_categoria'
            , 'data_venda'
            , 'nome_funcionario'
            , 'nome_categoria'
        ]

        colunas_para_update_merge = {
            'venda': configuracao_insert.excluded.venda,
            'data_procm': configuracao_insert.excluded.data_procm,
        }

        MensagemLog.exibir_mensagem("INFO", "Configurando a subida dos dados para a tabela destino")
        
        configuracao_upsert = (
            configuracao_insert # .WhenNotMatchedInsertAll()
            .on_conflict_do_update( # .WhenMatchedUpdate()
                index_elements = colunas_para_verificacao_insert,
                set_ = colunas_para_update_merge
            )
        )

        MensagemLog.exibir_mensagem("INFO", "Executando inserção dos dados transformados")
        
        conexao_postgres_destino = CarregamentoSetup.conector_postgres_destino.connect()

        conexao_postgres_destino.execute(configuracao_upsert)
        conexao_postgres_destino.close()

        MensagemLog.exibir_mensagem("INFO", "Inserção efetuada com sucesso")

    @staticmethod
    def executar_orquestracao_carregamento(nome_app: str) -> None:
            
        try:

            MensagemLog.exibir_mensagem("INFO", f"Iniciando app: {nome_app}")

            df_staging_vendas = (
                CarregamentoServico.obter_dados_vendas_staging(
                    CarregamentoSetup.data_inicio_extracao_dados
                )
            )

            df_staging_funcionarios = CarregamentoServico.obter_dados_funcionarios_staging()

            df_staging_categorias = CarregamentoServico.obter_dados_categorias_staging()

            df_tabela_completa_vendas_destino = (
                CarregamentoServico.cria_dataframe_fato(
                    df_staging_vendas
                    , df_staging_funcionarios
                    , df_staging_categorias
                )
            )

            nome_tabela_postgres_destino = 'tabela_completa_vendas'

            CarregamentoServico.persistir_dados_tabela_destino_postgres(df_tabela_completa_vendas_destino, nome_tabela_postgres_destino)

        except Exception as e:

            MensagemLog.exibir_mensagem("ERROR", "Processamento encerrou com erros")
            MensagemLog.exibir_mensagem("ERROR", str(e))

            traceback.print_exc()

        finally:
            MensagemLog.exibir_mensagem("INFO", "Processamento finalizado")

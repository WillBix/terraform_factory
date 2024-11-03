import requests
import pandas as pd
import traceback
from sqlalchemy import create_engine

from io import BytesIO
from datetime import datetime
from MensagemLog import MensagemLog
from IngestaoSetup import IngestaoSetup

class IngestaoServico:

    def __init__(self, data_inicio_processamento: str) -> None:

        self.data_inicio_processamento = data_inicio_processamento

    @staticmethod
    def obter_dados_funcionarios_origem_api(url_base_api: str) -> pd.DataFrame:

        id_funcionarios = list(range(1, 10))
        lista_resultado_das_requisicoes = []

        for id in id_funcionarios:

            url = f"{url_base_api}{id}"
            response = requests.get(url)

            if response.status_code == 200:

                try:
                    
                    nome_funcionario = response.text.strip()

                    estrutura_tabela_funcionarios = {
                        "id_funcionario": id
                        , "nome_funcionario": nome_funcionario
                        , "data_procm_ing_func": datetime.now()
                    }

                    lista_resultado_das_requisicoes.append(estrutura_tabela_funcionarios)

                except ValueError:

                    MensagemLog.exibir_mensagem("ERROR", f"Falha ao decodificar a URL: {url}")
                    
                    MensagemLog.exibir_mensagem("ERROR", "Resposta da API:", response.text)
            else:

                MensagemLog.exibir_mensagem("ERROR", f"Erro ao acessar a URL: {url}, Status Code: {response.status_code}")

        df_dados_provenientes_api = pd.DataFrame(lista_resultado_das_requisicoes)

        return df_dados_provenientes_api

    @staticmethod
    def obter_dados_vendas_origem_postgres(parametros_conexao_origem: str, data_inicio_processamento: str) -> pd.DataFrame:
        try:

            conector_postgres_origem = create_engine(parametros_conexao_origem)

            consulta_banco_origem = (
                "SELECT *, current_timestamp as data_procm_ing_vendas "
                "FROM public.venda WHERE data_venda >= %s"
            )

            df_dados_vendas_postgres = pd.read_sql_query(
                consulta_banco_origem,
                con = conector_postgres_origem,
                params = (data_inicio_processamento, )
            )

            return df_dados_vendas_postgres

        except Exception as e:

            MensagemLog.exibir_mensagem("ERROR", f"Erro ao conectar ao banco de dados: {e}")

            return pd.DataFrame()  

    @staticmethod
    def obter_dados_categorias_parquet_google(url_dados_categoria_vendas: str) -> pd.DataFrame:

        response = requests.get(url_dados_categoria_vendas)

        if response.status_code == 200:

            parquet_file = BytesIO(response.content)

            df_dados_categoria_vendas_completo = pd.read_parquet(parquet_file)

            df_dados_categoria_vendas_completo = (
                df_dados_categoria_vendas_completo
                .rename(
                    columns = {'id': 'id_categoria'}
                )
            )

            df_dados_categoria_vendas_completo['data_procm_ing_categoria'] = datetime.now()

            return df_dados_categoria_vendas_completo

        else:
            MensagemLog.exibir_mensagem("INFO", f"Falha ao baixar o arquivo: {response.status_code}")

            return None

    @staticmethod
    def executar_orquestracao_ingestao(nome_app: str) -> None:

        try:

            MensagemLog.exibir_mensagem("INFO", f"Iniciando app {nome_app}")            

            schema_destino = 'staging'

            nome_tabela_funcionario = 'funcionarios_stg'
            nome_tabela_vendas = 'vendas_stg'
            nome_tabela_categoria = 'categorias_stg'
            nome_tabela_controle_procm = 'controle_procm'

            MensagemLog.exibir_mensagem("INFO", "Extraindo e Persistindo dados de API")

            df_dados_func_api = (
                IngestaoServico.obter_dados_funcionarios_origem_api(IngestaoSetup.url_base_api)
            )

            df_dados_func_api.to_sql(
                nome_tabela_funcionario
                , con = IngestaoSetup.conector_postgres_destino
                , schema = schema_destino
                , if_exists = 'replace'
                , index = False
            )

            MensagemLog.exibir_mensagem("INFO", "Dados de API Persistidos")

            MensagemLog.exibir_mensagem("INFO", "Extraindo e Persistindo dados do Postgres")

            df_dados_vendas_postgres = (
                IngestaoServico.obter_dados_vendas_origem_postgres(
                    IngestaoSetup.string_de_conexao_postgres_origem
                    , IngestaoSetup.data_inicio_extracao_dados
                )
            )

            df_dados_vendas_postgres.to_sql(
                nome_tabela_vendas
                , con = IngestaoSetup.conector_postgres_destino
                , schema = schema_destino
                , if_exists = 'append'
                , index = False
            )

            MensagemLog.exibir_mensagem("INFO", "Dados do Postgres Persistidos")

            MensagemLog.exibir_mensagem("INFO", "Extraindo e Persistindo dados do GCP")

            df_dados_categoria_vendas_gcp = (
                IngestaoServico.obter_dados_categorias_parquet_google(IngestaoSetup.url_base_gcp)
            )

            df_dados_categoria_vendas_gcp.to_sql(
                nome_tabela_categoria
                , con = IngestaoSetup.conector_postgres_destino
                , schema = schema_destino
                , if_exists = 'replace'
                , index = False
            )

            MensagemLog.exibir_mensagem("INFO", "Dados do GCP Persistidos")

            MensagemLog.exibir_mensagem("INFO", "Adicionando Log Tabela de Controle")
            
            df_controle_procm = pd.DataFrame({
                'nome_aplic': nome_app,
                'data_procm': [datetime.now()]
            })

            df_controle_procm.to_sql(
                nome_tabela_controle_procm
                , con = IngestaoSetup.conector_postgres_destino
                , schema = schema_destino
                , if_exists = 'append'
                , index = False
            )

        except Exception as e:

            MensagemLog.exibir_mensagem("ERROR", "Processamento encerrou com erros")
            MensagemLog.exibir_mensagem("ERROR", str(e))

            traceback.print_exc()

        finally:
            MensagemLog.exibir_mensagem("INFO", "Processamento finalizado")


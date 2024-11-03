from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

from IngestaoServico import IngestaoServico
from IngestaoSetup import IngestaoSetup

from CarregamentoServico import CarregamentoServico
from CarregamentoSetup import CarregamentoSetup


# Argumentos
default_args = {
    'owner': 'William Caires'
    , 'depends_on_past': False
    , 'start_date': datetime(2024, 8, 31, 6, 0)
    , 'email': ['william.caires.15@gmail.com']
    , 'email_on_failure': False
    , 'email_on_retry': False
    , 'retries': 1
    , 'retry_delay': timedelta(minutes=1)
}

# DAG
dag_ingestao_dados = DAG(
    'projetoBixETL'
    , default_args = default_args
    , description = 'Projeto Bix Ingestão'
    , schedule_interval = '0 6 * * *'
    , is_paused_upon_creation = False
)

# PythonOperator
executa_ingestao_dados = PythonOperator(
    task_id = 'ingestao_dados_staging'
    , python_callable = lambda : IngestaoServico.executar_orquestracao_ingestao(IngestaoSetup.aplicacao_ingestao)
    , dag = dag_ingestao_dados
)

executa_carregamento_dados = PythonOperator(
    task_id = 'carregamento_dados_destino'
    , python_callable = lambda : CarregamentoServico.executar_orquestracao_carregamento(CarregamentoSetup.aplicacao_carregamento)
    , dag = dag_ingestao_dados
)

# Envia a tarefa para execução
executa_ingestao_dados >> executa_carregamento_dados




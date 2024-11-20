# Projeto 2 - Deploy do Stack de Treinamento Distribuído de Machine Learning com PySpark no Amazon EMR
# Script Principal

# Instala pacote Python dentro de código Python
import subprocess
comando = "pip install boto3"
subprocess.run(comando.split())

# Imports
import os
import boto3
import traceback
import pyspark 
from pyspark.sql import SparkSession
from p2_log import bix_grava_log
from p2_processamento import bix_limpa_transforma_data
from p2_ml import bix_cria_modelos_ml

# Nome do Bucket
NOME_BUCKET = "bix-p2-<id-aws>"

# Chaves de acesso à AWS
AWSACCESSKEYID = "coloque-aqui-sua-chave-aws"
AWSSECRETKEY = "coloque-aqui-sua-chave-aws"

print("\nLog bix - Inicializando o Processamento.")

# Cria um recurso de acesso ao S3 via código Python
s3_resource = boto3.resource('s3', aws_access_key_id = AWSACCESSKEYID, aws_secret_access_key = AWSSECRETKEY)

# Define o objeto de acesso ao bucket via Python
bucket = s3_resource.Bucket(NOME_BUCKET)

# Grava o log
bix_grava_log("Log bix - Bucket Encontrado.", bucket)

# Grava o log
bix_grava_log("Log bix - Inicializando o Apache Spark.", bucket)

# Cria a Spark Session e grava o log no caso de erro
try:
	spark = SparkSession.builder.appName("bixProjeto2").getOrCreate()
	spark.sparkContext.setLogLevel("ERROR")
except:
	bix_grava_log("Log bix - Ocorreu uma falha na Inicialização do Spark", bucket)
	bix_grava_log(traceback.format_exc(), bucket)
	raise Exception(traceback.format_exc())

# Grava o log
bix_grava_log("Log bix - Spark Inicializado.", bucket)

# Define o ambiente de execução do Amazon EMR
ambiente_execucao_EMR = False if os.path.isdir('data/') else True

# Bloco de limpeza e transformação
try:
	dataHTFfeaturized, dataTFIDFfeaturized, dataW2Vfeaturized = bix_limpa_transforma_data(spark, 
																							  bucket, 
																							  NOME_BUCKET, 
																							  ambiente_execucao_EMR)
except:
	bix_grava_log("Log bix - Ocorreu uma falha na limpeza e transformação dos data", bucket)
	bix_grava_log(traceback.format_exc(), bucket)
	spark.stop()
	raise Exception(traceback.format_exc())

# Bloco de criação dos modelos de Machine Learning
try:
	bix_cria_modelos_ml (spark, 
					     dataHTFfeaturized, 
					     dataTFIDFfeaturized, 
					     dataW2Vfeaturized, 
					     bucket, 
					     NOME_BUCKET, 
					     ambiente_execucao_EMR)
except:
	bix_grava_log("Log bix - Ocorreu Alguma Falha ao Criar os Modelos de Machine Learning", bucket)
	bix_grava_log(traceback.format_exc(), bucket)
	spark.stop()
	raise Exception(traceback.format_exc())

# Grava o log
bix_grava_log("Log bix - Modelos Criados e Salvos no S3.", bucket)

# Grava o log
bix_grava_log("Log bix - Processamento Finalizado com Sucesso.", bucket)

# Finaliza o Spark (encerra o cluster EMR)
spark.stop()




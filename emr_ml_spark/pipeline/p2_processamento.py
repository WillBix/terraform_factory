# Projeto 2 - Deploy do Stack de Treinamento Distribuído de Machine Learning com PySpark no Amazon EMR
# Processamento

# Imports
import os
import os.path
import numpy
from pyspark.ml.feature import * 
from pyspark.sql import functions
from pyspark.sql.functions import * 
from pyspark.sql.types import StringType,IntegerType
from pyspark.ml.classification import *
from pyspark.ml.evaluation import *
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import StopWordsRemover
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from p2_log import bix_grava_log
from p2_upload_s3 import bix_upload_data_processados_bucket

# Define uma função para calcular a quantidade e a porcentagem de valores nulos em cada coluna de um DataFrame
def bix_calcula_valores_nulos(df):
    
    # Inicializa uma lista vazia para armazenar o resultado de contagem de nulos
    null_columns_counts = []
    
    # Conta o número total de linhas no DataFrame
    numRows = df.count()

    # Itera sobre cada coluna no DataFrame
    for k in df.columns:
        
        # Conta o número de linhas nulas na coluna atual
        nullRows = df.where(col(k).isNull()).count()
        
        # Verifica se o número de linhas nulas é maior que zero
        if(nullRows > 0):
            
            # Cria uma tupla com o nome da coluna, número de nulos e a porcentagem de nulos
            temp = k, nullRows, (nullRows / numRows) * 100
            
            # Adiciona a tupla à lista de resultados
            null_columns_counts.append(temp)

    # Retorna a lista de colunas com a contagem e porcentagem de valores nulos
    return null_columns_counts

# Função para limpeza e transformação
def bix_limpa_transforma_data(spark, bucket, nome_bucket, ambiente_execucao_EMR):
	
	# Define o caminho para armazenar o resultado do processamento
	path =  f"s3://{nome_bucket}/data/" if ambiente_execucao_EMR else  "data/"

	# Grava no log
	bix_grava_log("Log bix - Importando os data...", bucket)

	# Carrega o arquivo CSV
	reviews = spark.read.csv(path+'dataset.csv', header=True, escape="\"")

	# Grava no log
	bix_grava_log("Log bix - data Importados com Sucesso.", bucket)
	bix_grava_log("Log bix - Total de Registros: " + str(reviews.count()), bucket)
	bix_grava_log("Log bix - Verificando se Existem data Nulos.", bucket)

	# Calcula os valores ausentes
	null_columns_calc_list = bix_calcula_valores_nulos(reviews)

	# Ação com base nos valores ausentes
	if (len(null_columns_calc_list) > 0):
		for column in null_columns_calc_list:
			bix_grava_log("Coluna " + str(column[0]) + " possui " + str(column[2]) + " de data nulos", bucket)
		reviews = reviews.dropna()
		bix_grava_log("data nulos excluídos", bucket)
		bix_grava_log("Log bix - Total de Registros Depois da Limpeza: " + str(reviews.count()), bucket)
	else:
		bix_grava_log("Log bix - Valores Ausentes Nao Foram Detectados.", bucket)

	# Grava no log
	bix_grava_log("Log bix - Verificando o Balanceamento de Classes.", bucket)
	
	# Conta os registros de avaliações positivas e negativas
	count_positive_sentiment = reviews.where(reviews['sentiment'] == "positive").count()
	count_negative_sentiment = reviews.where(reviews['sentiment'] == "negative").count()

	# Grava no log
	bix_grava_log("Log bix - Existem " + str(count_positive_sentiment) + " reviews positivos e " + str(count_negative_sentiment) + " reviews negativos", bucket)

	# Cria o dataframe
	df = reviews

	# Grava no log
	bix_grava_log("Log bix - Transformando os data", bucket)
	
	# Cria o indexador
	indexer = StringIndexer(inputCol="sentiment", outputCol="label")
	
	# Treina o indexador
	df = indexer.fit(df).transform(df)

	# Grava no log
	bix_grava_log("Log bix - Limpeza dos data", bucket)
	
	# Remove caracteres especiais dos data de texto
	df = df.withColumn("review", regexp_replace(df["review"], '<.*/>', ''))
	df = df.withColumn("review", regexp_replace(df["review"], '[^A-Za-z ]+', ''))
	df = df.withColumn("review", regexp_replace(df["review"], ' +', ' '))
	df = df.withColumn("review", lower(df["review"]))

	# Grava no log
	bix_grava_log("Log bix - Os data de Texto Foram Limpos", bucket)
	bix_grava_log("Log bix - Tokenizando os data de Texto.", bucket)

	# Cria o tokenizador (converte data de texto em representações numéricas)
	regex_tokenizer = RegexTokenizer(inputCol="review", outputCol="words", pattern="\\W")

	# Aplica o tokenizador
	df = regex_tokenizer.transform(df)

	# Grava no log
	bix_grava_log("Log bix - Removendo Stop Words.", bucket)

	# Cria o objeto para remover stop words
	remover = StopWordsRemover(inputCol="words", outputCol="filtered")

	# Aplica o objeto e remove stop words
	feature_data = remover.transform(df)

	# Grava no log
	bix_grava_log("Log bix - Aplicando HashingTF.", bucket)

	# Cria e aplica o processador de texto
	hashingTF = HashingTF(inputCol="filtered", outputCol="rawfeatures", numFeatures=250)
	HTFfeaturizedData = hashingTF.transform(feature_data)

	# Grava no log
	bix_grava_log("Log bix - Aplicando IDF.", bucket)

	# Cria e aplica o processador de texto
	idf = IDF(inputCol="rawfeatures", outputCol="features")
	idfModel = idf.fit(HTFfeaturizedData)
	TFIDFfeaturizedData = idfModel.transform(HTFfeaturizedData)
	
	# Ajusta o nome dos objetos
	TFIDFfeaturizedData.name = 'TFIDFfeaturizedData'
	HTFfeaturizedData = HTFfeaturizedData.withColumnRenamed("rawfeatures","features")
	HTFfeaturizedData.name = 'HTFfeaturizedData' 

	# Grava no log
	bix_grava_log("Log bix - Aplicando Word2Vec.", bucket)

	# Cria e aplica o processador de texto
	word2Vec = Word2Vec(vectorSize=250, minCount=5, inputCol="filtered", outputCol="features")
	model = word2Vec.fit(feature_data)
	W2VfeaturizedData = model.transform(feature_data)

	# Grava no log
	bix_grava_log("Log bix - Padronizando os data com MinMaxScaler.", bucket)

	# Cria e aplica o padronizador
	scaler = MinMaxScaler(inputCol="features", outputCol="scaledFeatures")
	scalerModel = scaler.fit(W2VfeaturizedData)
	scaled_data = scalerModel.transform(W2VfeaturizedData)
	
	# Ajusta o nome dos objetos
	W2VfeaturizedData = scaled_data.select('sentiment','review','label','scaledFeatures')
	W2VfeaturizedData = W2VfeaturizedData.withColumnRenamed('scaledFeatures','features')
	W2VfeaturizedData.name = 'W2VfeaturizedData'

	# Grava no log
	bix_grava_log("Log bix - Salvando os data Limpos e Transformados.", bucket)

	# Define o caminho para salvar o resultado
	path = f"s3://{nome_bucket}/data/" if ambiente_execucao_EMR else 'data/'
	s3_path = 'data/'

	# Upload para o bucket S3
	bix_upload_data_processados_bucket(HTFfeaturizedData, path + 'HTFfeaturizedData', s3_path + 'HTFfeaturizedData' , bucket, ambiente_execucao_EMR)
	bix_upload_data_processados_bucket(TFIDFfeaturizedData, path + 'TFIDFfeaturizedData', s3_path + 'TFIDFfeaturizedData', bucket, ambiente_execucao_EMR)
	bix_upload_data_processados_bucket(W2VfeaturizedData, path + 'W2VfeaturizedData', s3_path + 'W2VfeaturizedData', bucket, ambiente_execucao_EMR)

	return HTFfeaturizedData, TFIDFfeaturizedData, W2VfeaturizedData


	
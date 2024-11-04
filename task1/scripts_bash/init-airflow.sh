#!/bin/bash

# Atualizar pacotes
sudo apt update

# Instalar pacotes necessários
sudo apt install -y python3-pip
sudo apt install -y sqlite3
sudo apt install -y python3.10-venv
sudo apt-get install -y libpq-dev
sudo apt-get install -y postgresql postgresql-contrib

# Criar e ativar um ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar Airflow com suporte ao Postgres
pip install "apache-airflow[postgres]==2.5.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.0/constraints-3.7.txt"

# Inicializar o banco de dados do Airflow
airflow db init

# Configurar o banco de dados PostgreSQL
sudo -u postgres psql <<EOF
CREATE DATABASE airflow;
CREATE USER airflow WITH PASSWORD 'airflow';
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
EOF

# Atualizar a configuração do Airflow
sed -i 's#sqlite:////home/ubuntu/airflow/airflow.db#postgresql+psycopg2://airflow:airflow@localhost/airflow#g' airflow.cfg
sed -i 's#SequentialExecutor#LocalExecutor#g' airflow.cfg

# Inicializar novamente o banco de dados do Airflow
airflow db init

# Criar um usuário para o Airflow
airflow users create -u airflow -f airflow -l airflow -r Admin -e william.caires@bix-tech.com

# Iniciar o webserver e o scheduler do Airflow
airflow webserver &
airflow scheduler

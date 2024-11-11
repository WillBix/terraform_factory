# Imagem oficial do Ubuntu como base
FROM ubuntu:latest

LABEL maintainer="WILL-BIX"

# Atualizar os pacotes do sistema e instalar dependências necessárias
RUN apt-get update && \
    apt-get install -y wget unzip curl openssh-client iputils-ping python3 python3-pip python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Criar um ambiente virtual e instalar pacotes Python
RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install pandas scikit-learn joblib

# Adicionar o ambiente virtual ao PATH e definir o PYTHONPATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/venv/lib/python3.8/site-packages"

# Definir a versão do Terraform (ajuste conforme necessário)
ENV TERRAFORM_VERSION=1.6.5

# Baixar e instalar Terraform
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Criar a pasta /exemplos como um ponto de montagem para um volume
RUN mkdir /exemplos
VOLUME /exemplos

# Criar a pasta Downloads e instalar o AWS CLI (para acessar a AWS)
RUN mkdir Downloads && \
    cd Downloads && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    cd .. && rm -rf Downloads

# Definir o comando padrão para execução quando o container for iniciado
CMD ["/bin/bash"]

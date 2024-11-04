provider "aws" {
  region = "us-east-2"
}

# Security Group para permitir tráfego de entrada
resource "aws_security_group" "airflow_sg" {
  name        = "terraform_ingress" 
  description = "Grupo de seguranca para permitir trafego de entrada"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Permitir SSH de qualquer IP
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Permitir acesso à porta 8080 (Airflow)
  }
}

# Security Group para permitir tráfego de saída
resource "aws_security_group" "allow_all_traffic_egress" {
  name        = "terraform_egress" 
  description = "Grupo de seguranca para permitir todo o trafego de saida"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # Permitir todo o tráfego de saída
  }
}

# Carregar o script de inicialização
data "template_file" "init" {
  template = file("scripts_bash/init-airflow.sh")
}

# Instância EC2
resource "aws_instance" "airflow_instance" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  security_groups        = [aws_security_group.airflow_sg.name]
  
  vpc_security_group_ids = [aws_security_group.allow_all_traffic_egress.id] 

  associate_public_ip_address = true
  user_data = data.template_file.init.rendered

  tags = {
    Name = "Airflow-EC2-Instance"
  } 
}

# Atribuir um IP elástico à instância
resource "aws_eip" "public_ip" {
  instance = aws_instance.airflow_instance.id  # Corrigido para referenciar a instância correta
  vpc      = true
}

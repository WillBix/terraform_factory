provider "aws" {
  region = "us-east-2"
}

resource "aws_security_group" "airflow_sg" {
  name        = "airflow_security_group"
  description = "Permitir SSH e acesso HTTP para o Airflow"

  ingress {
    description = "Inbound Rule"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Acesso SSH aberto
  }

  ingress {
    description = "Inbound Rule"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Porta padrão do Airflow
  }

  egress {
    description = "Outbound Rule"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "airflow_instance" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.key_name
  security_groups = [aws_security_group.airflow_sg.name]

  # Lê o conteúdo do arquivo init-airflow.sh e o coloca no user_data
  user_data = file("scripts/init-airflow.sh")

  tags = {
    Name = "Airflow-EC2-Instance"
  }

  # Provisioners para configurar o Airflow e copiar DAGs, se necessário
  provisioner "file" {
    source      = "/terraform_factory/task1/dags/" # Diretório local com DAGs
    destination = "/home/ec2-user/airflow/dags"    # Destino na instância EC2

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = file("bix_kp.pem")
      host        = self.public_ip  # evitar referência cíclica
    }
  }

  provisioner "remote-exec" {
    inline = [
      "sudo chown -R ec2-user:ec2-user /home/ec2-user/airflow/dags",
      "nohup airflow webserver --port 8080 &",
      "nohup airflow scheduler &"
    ]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = file("bix_kp.pem")
      host        = self.public_ip  # evitar referência cíclica
    }
  }
}

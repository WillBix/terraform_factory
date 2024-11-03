provider "aws" {
  region = "us-east-1" # Ajuste a região conforme necessário
}

resource "aws_security_group" "airflow_sg" {
  name        = "airflow_security_group"
  description = "Permitir SSH e acesso HTTP para o Airflow"

  ingress {
    from_port   = 22
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Acesso SSH aberto
  }

  ingress {
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

  egress {
    description = "Outbound Rule"
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "airflow_instance" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.key_name
  security_groups = [aws_security_group.airflow_sg.name]

  # Script de inicialização para instalar o Airflow
  user_data = <<-EOF
              #!/bin/bash
              sudo yum update -y
              sudo yum install -y python3 python3-pip
              pip3 install apache-airflow
              airflow db init
              EOF

  # Provisioner para configurar permissões e iniciar o Airflow
  provisioner "remote-exec" {
    inline = [
      "sudo mkdir -p /home/ec2-user/airflow/dags",
      "sudo cp -r /home/ec2-user/airflow/dags/* terraform_factory/task1/dags/", # Ajuste conforme o local padrão de instalação do Airflow
      "nohup airflow webserver --port 8080 &",
      "nohup airflow scheduler &"
    ]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = file("bix_kp.pem")
      host        = aws_instance.airflow_instance.public_ip
    }
  }

  # Provisioner para copiar o diretório de DAGs
  provisioner "file" {
    source      = "/task1/dags/"                # Diretório local com DAGs
    destination = "/home/ec2-user/airflow/dags" # Destino na instância EC2
  }


  tags = {
    Name = "Airflow-EC2-Instance"
  }
}


# Conecta no provedor
provider "aws" {
  region = var.region  # Define a região onde os recursos da AWS serão criados (us-east-2)
}

# Configuração do S3 para armazenar os arquivos da aplicação

resource "aws_s3_bucket" "bix_bucket_flask" {
  bucket = "bix-182399724833-bucket"  # Nome do bucket S3 a ser criado

  tags = {
    Name        = "BIX Bucket"        # Adiciona a tag 'Name' para identificação do bucket
    Environment = "TaskML"            # Adiciona a tag 'Environment' para indicar o ambiente
  }

  provisioner "local-exec" {
    command = "${path.module}/upload_to_s3.sh"  # Executa um script local para fazer upload de arquivos para o S3
  }

  provisioner "local-exec" {
    when    = destroy  # Esse provisioner é executado quando o recurso é destruído
    command = "aws s3 rm s3://bix-182399724833-bucket --recursive"  # Remove todos os arquivos do bucket ao destruir o recurso
  }
}

# Subindo o servidor no EC2
resource "aws_instance" "bix_ml_api" {

  count = var.create_instance ? var.instance_count : 0

  ami = var.ami  # AMI (Imagem da Máquina Virtual) para a instância EC2
  instance_type = var.instance_type  # Tipo da instância EC2, no caso 't2.micro'

  iam_instance_profile = aws_iam_instance_profile.ec2_s3_profile.name  # Associa um perfil IAM à instância EC2 para permitir acesso ao S3

  vpc_security_group_ids = [aws_security_group.bix_ml_api_sg.id]  # Associando a instância EC2 ao grupo de segurança

  # Script de inicialização (user_data) que será executado na inicialização da instância EC2
  user_data = <<-EOF
                #!/bin/bash
                sudo yum update -y
                sudo yum install -y python3 python3-pip awscli
                sudo pip3 install flask joblib scikit-learn numpy scipy gunicorn
                sudo mkdir /bix_ml_app
                sudo aws s3 sync s3://bix-182399724833-bucket /bix_ml_app
                cd /bix_ml_app
                nohup gunicorn -w 4 -b 0.0.0.0:5000 app:app & 
              EOF

  tags = {
    Name = "bixFlaskApp-${count.index}"  # Nome da instância EC2 para fácil identificação
  }
}

# Configurando o SG para acessar portas no EC2
resource "aws_security_group" "bix_ml_api_sg" {
  name        = "bix_ml_api_sg"  
  description = "Security Group for Flask App in EC2"

  ingress {
    description = "Inbound Rule 1"  # Regra de entrada para permitir o tráfego HTTP (porta 80)
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Permite acesso de qualquer IP
  }

  ingress {
    description = "Inbound Rule 2"  # Regra de entrada para permitir o tráfego Flask (porta 5000)
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  
  }

  # Acessar o EC2 via web
  ingress {
    description = "Inbound Rule 3"  # Regra de entrada para permitir SSH (porta 22)
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Outbound Rule"  # Regra de saída que permite tráfego para qualquer porta
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Cria um perfil de acesso para a comunicação entre EC2 e S3
resource "aws_iam_role" "ec2_s3_access_role" {
  name = "ec2_s3_access_role" 

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",  # Permite à EC2 assumir essa role
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"  # O serviço EC2 é quem pode assumir essa role
        }
      },
    ]
  })
}

# Política do S3 - Permissões
resource "aws_iam_role_policy" "s3_access_policy" {
  name = "s3_access_policy"
  role = aws_iam_role.ec2_s3_access_role.id 

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject",  # Permite obter objetos do S3
          "s3:PutObject",  # Permite colocar objetos no S3
          "s3:ListBucket"  # Permite listar objetos no bucket S3
        ],
        Effect = "Allow",  # Permite essas ações
        Resource = [
          "${aws_s3_bucket.bix_bucket_flask.arn}/*",  # Aplica a política a todos os objetos dentro do bucket
          "${aws_s3_bucket.bix_bucket_flask.arn}"    # Aplica a política também ao próprio bucket
        ]
      },
    ]
  })
}

# Cria um perfil de instância IAM para a EC2 com as permissões definidas na role
resource "aws_iam_instance_profile" "ec2_s3_profile" {
  name = "ec2_s3_profile"  # Nome do perfil IAM
  role = aws_iam_role.ec2_s3_access_role.name  # Associa a role criada ao perfil IAM
}

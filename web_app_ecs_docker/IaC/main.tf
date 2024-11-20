# Define um cluster ECS com um nome baseado nas variáveis do projeto e do ambiente 
resource "aws_ecs_cluster" "ecs-cluster" {
  name = "${var.project_name}-${var.env}-cluster"
}

# Define um grupo de logs do CloudWatch com um nome baseado nas variáveis do projeto e do ambiente
resource "aws_cloudwatch_log_group" "ecs-log-group" {
  name              = "/ecs/${var.project_name}-${var.env}-task-definition"
  retention_in_days = 7
}

# Recurso de definição de tarefa do ECS com as configurações necessárias, incluindo definições de container
resource "aws_ecs_task_definition" "ecs-task" {
  family                   = "${var.project_name}-${var.env}-task-definition"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu    # Unidades de CPU para a tarefa
  memory                   = var.memory # Memória em MB para a tarefa
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn              = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-${var.env}-con"
      image = var.docker_image_name                # Nome da Imagem Docker com a aplicação web
      essential : true

      portMappings = [
        {
          containerPort = tonumber(var.container_port)
          hostport      = tonumber(var.container_port)
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ],

      # Adicionar arquivo de variáveis de ambiente do S3
      environmentFiles = [
        {
          value = "arn:aws:s3:::${aws_s3_bucket.bix_bucket_ecs.bucket}/${aws_s3_object.vars_env.key}"
          type  = "s3"
        }
      ],

      # Configurar AWS CloudWatch Logs para container
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-create-group"  = "true"
          "awslogs-group"         = aws_cloudwatch_log_group.ecs-log-group.name
          "awslogs-region"        = var.awslogs_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# Recurso de serviço ECS com tipo de inicialização Fargate, especificando a configuração de rede
resource "aws_ecs_service" "ecs-service" {
  name            = "${var.project_name}-service"
  launch_type     = "FARGATE"
  cluster         = aws_ecs_cluster.ecs-cluster.id
  task_definition = aws_ecs_task_definition.ecs-task.arn
  desired_count   = 1

  # Define configurações de rede para o serviço ECS
  network_configuration {
    assign_public_ip = true
    subnets          = [module.vpc.public_subnets[0]]                      
    security_groups  = [module.container-security-group.security_group_id] # Firewall da AWS
  }

  # Configura o balanceamento de carga para o serviço ECS
  health_check_grace_period_seconds = 0
  load_balancer {
    target_group_arn = aws_lb_target_group.ecs-target-group.arn
    container_name   = "${var.project_name}-${var.env}-con"
    container_port   = var.container_port
  }
}

# Define o Application Load Balancer (ALB)
resource "aws_lb" "ecs-alb" {
  name               = "${var.project_name}-${var.env}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.alb-security-group.security_group_id]                
  subnets            = [module.vpc.public_subnets[0], module.vpc.public_subnets[1]] 
}

# Define o Target Group
resource "aws_lb_target_group" "ecs-target-group" {
  name        = "${var.project_name}-${var.env}-target-group"
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = module.vpc.vpc_id 

  health_check {
    path                = var.health_check_path 
    protocol            = "HTTP"
    matcher             = "200-299"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 5
    unhealthy_threshold = 2
  }
}

# O Listener associa o ALB com o Target Group
resource "aws_lb_listener" "ecs-listener" {
  load_balancer_arn = aws_lb.ecs-alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs-target-group.arn
  }
}

resource "aws_s3_bucket" "bix_bucket_ecs" {
  bucket = "bix-task-seu-id-aws>"  # Nome do bucket S3 a ser criado (Esse nome se refere ao id da conta de quem criou o script, altere o ID)

  tags = {
    Name        = "BIX Bucket"        # Adiciona a tag 'Name' para identificação do bucket
    Environment = "TaskECS"            # Adiciona a tag 'Environment' para indicar o ambiente
  }

  provisioner "local-exec" {
    when    = destroy  # Esse provisioner é executado quando o recurso é destruído
    command = "aws s3 rm s3://bix-task-<seu-id-aws> --recursive"  # Remove todos os arquivos do bucket ao destruir o recurso
  }
}

# Gerencia o upload do arquivo vars.env
resource "aws_s3_object" "vars_env" {
  bucket       = aws_s3_bucket.bix_bucket_ecs.bucket 
  key          = "vars.env"                          # Caminho/nome do arquivo no bucket
  source       = "/web_app_ecs_docker/IaC/vars.env"  # Caminho local do arquivo
  content_type = "text/plain"
}

# Cria uma role IAM para ECS Tasks
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs_task_execution_role"  # Nome da role IAM

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",  # Permite a Task do ECS assumir essa role
        Effect = "Allow",
        Principal = {
          Service = [
            "ecs-tasks.amazonaws.com" # Serviço ECS Tasks que pode assumir a role
          ]  
        }
      },
    ]
  })
}

# Anexa a política AmazonECS_FullAccess
resource "aws_iam_role_policy_attachment" "ecs_full_access" {
  role       = aws_iam_role.ecs_task_execution_role.name  # Associa à role criada
  policy_arn = "arn:aws:iam::aws:policy/AmazonECS_FullAccess"  # Política de acesso completo ao ECS
}

# Anexa a política AmazonECSTaskExecutionRolePolicy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name  # Associa à role criada
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"  # Política de execução de tarefas ECS
}

# Anexa a política AmazonS3FullAccess
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.ecs_task_execution_role.name  # Associa à role criada
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"  # Política de acesso completo ao S3
}


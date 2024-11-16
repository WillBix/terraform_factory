# Definindo ALB DNS Output 
output "alb_dns_name" {
  value = aws_lb.ecs-alb.dns_name
}

# Se algum usuário for entrar no seu site com base no que está configurado aqui, o endereço DNS sairia alog como alb_dns_name.aws.amazon.com
# Como fica algo que não é comercialmente atraente, você precisaria de um serviço de DNS.
# A AWS tem o Route 53. Você precisaria configurá-lo para receber esses DNS e renomeá-los conforme necessidade.

output "ec2_public_ip" {
  description = "Endereço IP público da instância EC2 com Airflow"
  value       = aws_instance.airflow_instance.public_ip
}
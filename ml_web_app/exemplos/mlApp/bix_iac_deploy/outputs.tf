output "instance_public_dns" {
  value = [for instance in aws_instance.bix_ml_api : instance.public_dns]
}

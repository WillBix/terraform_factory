variable "key_name" {
  description = "Nome do par de chaves para acessar a instância"
  type        = string
}

variable "instance_type" {
  type        = string
  description = "Tipo da instância EC2"
}

variable "ami_id" {
  description = "ID da AMI (Amazon Linux 2)"
  type = string
}

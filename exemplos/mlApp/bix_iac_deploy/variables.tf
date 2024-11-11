# Definindo uma variável de string
variable "region" {
  description = "A região da AWS"
  type        = string
  default     = "us-east-1"
}

# Definindo uma variável de lista
variable "instance_type" {
  description = "Tipo de instância"
  type        = string
}

# Definindo uma variável obrigatória
variable "instance_count" {
  description = "Número de instâncias"
  type        = number
}

variable "create_instance" {
  description = "Flag para criar ou não a instância"
  type        = bool
  default     = true
}

variable "ami" {
  description = "AMI da instância EC2"
  type        = string
}


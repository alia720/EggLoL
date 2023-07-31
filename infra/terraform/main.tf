# Terraform
terraform {
  required_providers {
    aws = {
        version = ">= 4.0.0"
        source = "hashicorp/aws"
    }
  }
}

# Region
provider "aws" {
    region = "us-west-2"
}

# Random String
resource "random_string" "password" {
    length = 16
    upper = true
    numeric = true
    special = false
}

# VPC
data "aws_vpc" "default" {
    default = true
}

# Security Group
resource "aws_security_group" "security_group-eggLoL" {
    vpc_id = "${data.aws_vpc.default.id}"
    name = "security_group-eggLoL"
    description = "Allow all inbound for PostgreSQL"
}

# Ingress Rule
resource "aws_vpc_security_group_ingress_rule" "ingress_rule-egglol" {
    security_group_id = aws_security_group.security_group-eggLoL.id
    from_port   = 5432
    to_port     = 5432
    ip_protocol = "tcp"
    cidr_ipv4   = "0.0.0.0/0"
}

# PostgreSQL Instance
resource "aws_db_instance" "postgresql-egglol" {
  identifier = "postgresql-egglol"
  engine = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  vpc_security_group_ids = [aws_security_group.security_group-eggLoL.id]
  publicly_accessible = true
  db_name = "egglol"
  username = "egglol"
  password = "${random_string.password.result}"

  multi_az = false
  backup_retention_period = 7
}
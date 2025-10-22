resource "aws_security_group" "api_sg" {
  name        = var.api_sg_name
  description = "Allow SSH, ICMP and HTTP"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Inbound API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow ICMP (ping)"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.api_sg_name
  }
}

resource "aws_security_group" "vdb_sg" {
  name        = var.vdb_sg_name
  description = "Vector DB security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "OpenSearch from Lambda functions"
    from_port       = 9200
    to_port         = 9200
    protocol        = "tcp"
    security_groups = [aws_security_group.api_sg.id]
  }

  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.api_sg.id]
  }

  ingress {
    description = "OpenSearch from VPC"
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  ingress {
    description = "OpenSearch management port from VPC"
    from_port   = 9600
    to_port     = 9600
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.vdb_sg_name
  }
}

resource "aws_security_group" "rdb_sg" {
  name        = var.rdb_sg_name
  vpc_id      = aws_vpc.main.id
  description = "Relational DB security group"

  ingress {
    from_port       = var.postgres_port
    to_port         = var.postgres_port
    protocol        = "tcp"
    self            = true
    security_groups = [aws_security_group.api_sg.id]
  }

  ingress {
    from_port       = -1
    to_port         = -1
    protocol        = "icmp"
    security_groups = [aws_security_group.api_sg.id]
  }

  egress {
    from_port       = var.postgres_port
    to_port         = var.postgres_port
    protocol        = "tcp"
    self            = true
    security_groups = [aws_security_group.api_sg.id]
  }
}

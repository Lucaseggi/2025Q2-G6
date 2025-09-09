resource "aws_security_group" "public_sg" {
  name        = var.api_sg_name
  description = "Allow SSH and HTTP"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
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
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.api_sg_name
  }
}

resource "aws_security_group" "private_sg" {
  name        = var.priv_sg_name
  description = "Private instances SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow HTTP from public SG"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.public_sg.id]
  }

  ingress {
    description     = "Allow SSH from public SG (optional, e.g., for bastion)"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.public_sg.id]
  }

  ingress {
    description     = "Allow RabbitMQ traffic from private SG"
    from_port       = 5672
    to_port         = 5672
    protocol        = "tcp"
    self            = true
  }

  ingress {
    description = "Inbound for embedder"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.priv_sg_name
  }
}


resource "aws_security_group" "vdb_sg" {
  name        = var.vdb_sg_name
  description = "Private instances SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow HTTP from public SG"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.public_sg.id, aws_security_group.private_sg.id]
  }

  ingress {
    description     = "Allow SSH from public SG (optional, e.g., for bastion)"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.public_sg.id, aws_security_group.private_sg.id]
  }

  ingress {
    description = "OpenSearch"
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    self        = true
    security_groups = [aws_security_group.public_sg.id, aws_security_group.private_sg.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.vdb_sg_name
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "tls_private_key" "master-tls-key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "master-key" {
  key_name   = "master-key"
  public_key = tls_private_key.master-tls-key.public_key_openssh
}

resource "aws_instance" "api-rest" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.public1.id
  security_groups        = [aws_security_group.public_sg.id]
  associate_public_ip_address = true
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.api_rest_name
  }
}

resource "aws_instance" "scrapper-ms" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private1.id
  security_groups        = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.scrapper_ms_name
  }
}

resource "aws_instance" "processing-ms" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private1.id
  security_groups        = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.processing_ms_name
  }
}

resource "aws_instance" "embedding-ms" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private1.id
  security_groups        = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.embedding_ms_name
  }
}

resource "aws_instance" "inserter-ms" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private1.id
  security_groups        = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.inserter_ms_name
  }
}

resource "aws_instance" "queue" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private1.id
  security_groups        = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.queue_name
  }
}

resource "aws_instance" "vector-db" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.default_instance_type
  subnet_id              = aws_subnet.private2.id
  security_groups        = [aws_security_group.vdb_sg.id]
  associate_public_ip_address = false
  key_name               = aws_key_pair.master-key.key_name

  tags = {
    Name = var.queue_name
  }
}

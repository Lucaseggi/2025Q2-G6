data "aws_ami" "ecs" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

resource "tls_private_key" "master_tls_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "master_key" {
  key_name   = "master-key"
  public_key = tls_private_key.master_tls_key.public_key_openssh
}

# Bastion Host in public subnet for accessing private resources
# Conditional creation based on enable_bastion variable
resource "aws_instance" "bastion" {
  count                       = var.enable_bastion ? 1 : 0
  ami                         = data.aws_ami.ecs.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public_1.id
  vpc_security_group_ids      = [aws_security_group.api_sg.id, aws_security_group.vdb_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.master_key.key_name

  tags = {
    Name = "simpla-bastion"
  }
}

# OpenSearch Vector DB in private subnet
resource "aws_instance" "vector_db" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = "m7i-flex.large"
  subnet_id                   = aws_subnet.private_1.id
  vpc_security_group_ids      = [aws_security_group.vdb_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master_key.key_name

  tags = {
    Name = var.vdb_name
  }
}

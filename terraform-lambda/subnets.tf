data "aws_availability_zones" "available" {}

# Public subnets
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[0]
  cidr_block              = var.public_subnet_1_cidr
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-1"
  }
}

# Private subnets
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[0]
  cidr_block        = var.private_subnet_1_cidr

  tags = {
    Name = "private-subnet-1"
  }
}

# Private subnets
resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[1]
  cidr_block        = var.private_subnet_2_cidr

  tags = {
    Name = "private-subnet-2"
  }
}

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "aurora-private-subnet-group"
  subnet_ids = [
    aws_subnet.private_1.id,
    aws_subnet.private_2.id
  ]

  tags = {
    Name = "aurora-private-subnet-group"
  }
}
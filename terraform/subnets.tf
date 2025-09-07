data "aws_availability_zones" "available" {}

# Public subnets
resource "aws_subnet" "public1" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[0]
  cidr_block              = var.public_subnet_1_cidr
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-1"
  }
}

resource "aws_subnet" "public2" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[1]
  cidr_block              = var.public_subnet_2_cidr
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-2"
  }
}

# Private subnets
resource "aws_subnet" "private1" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[0]
  cidr_block        = var.private_subnet_1_cidr

  tags = {
    Name = "private-subnet-1"
  }
}

resource "aws_subnet" "private2" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[0]
  cidr_block        = var.private_subnet_2_cidr

  tags = {
    Name = "private-subnet-2"
  }
}

resource "aws_subnet" "private3" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[1]
  cidr_block        = var.private_subnet_3_cidr

  tags = {
    Name = "private-subnet-3"
  }
}

resource "aws_subnet" "private4" {
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[1]
  cidr_block        = var.private_subnet_4_cidr

  tags = {
    Name = "private-subnet-4"
  }
}
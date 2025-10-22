# NAT Gateway - Conditional creation based on enable_nat_gateway variable
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public_1.id
  depends_on    = [aws_internet_gateway.main_igw]

  tags = {
    Name = "main-nat"
  }
}

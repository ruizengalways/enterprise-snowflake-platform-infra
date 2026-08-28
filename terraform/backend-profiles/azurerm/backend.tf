# Materialized into a Terraform root at runtime by terraform/scripts/select-backend.sh.
# Backend credentials and resource identifiers are supplied externally.
terraform {
  backend "azurerm" {}
}

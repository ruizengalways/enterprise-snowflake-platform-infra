# Authentication is external to source control. GitHub Actions authenticates as
# SU_GITHUB_TERRAFORM_UAT through OIDC WIF; both lifecycle provider aliases use
# the same least-privilege routine Terraform role.
provider "snowflake" {
  alias = "objects"
  role  = local.config.terraform_identity.role_name
}

provider "snowflake" {
  alias = "security"
  role  = local.config.terraform_identity.role_name
}

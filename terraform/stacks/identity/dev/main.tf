locals {
  config = yamldecode(file("${path.root}/../../../../config/environments/dev.yml"))
}

module "workload_identity" {
  source = "../../../modules/workload-identity"

  service_user_name = local.config.terraform_identity.user_name
  role_name         = local.config.terraform_identity.role_name
  oidc_issuer       = local.config.terraform_identity.oidc_issuer
  oidc_subject      = local.config.terraform_identity.oidc_subject
  oidc_audience     = var.oidc_audience
}

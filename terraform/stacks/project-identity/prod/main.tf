locals {
  config = yamldecode(file("${path.root}/../../../../config/environments/prod.yml"))

  project_deploy_identities = {
    for project_key, project in local.config.projects :
    project_key => {
      project_code      = project.code
      service_user_name = "SU_GITHUB_${project.code}_DEPLOY"
      role_name         = "AR_${project.code}_DEPLOY"
      oidc_subject      = "repo:${local.config.project_deploy_identity.github_owner}/${project.repository}:environment:${local.config.project_deploy_identity.github_environment}"
    }
  }
}

module "project_deploy_identity" {
  source   = "../../../modules/service-identity"
  for_each = local.project_deploy_identities

  service_user_name = each.value.service_user_name
  role_name         = each.value.role_name
  oidc_issuer       = local.config.project_deploy_identity.oidc_issuer
  oidc_subject      = each.value.oidc_subject
  oidc_audience     = var.oidc_audience
  comment           = "GitHub Actions ${each.value.project_code} PROD deployment identity; managed by enterprise-snowflake-platform-infra."
}

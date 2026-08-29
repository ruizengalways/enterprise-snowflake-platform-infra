output "project_deploy_service_users" {
  description = "Project PROD deployment Snowflake SERVICE users keyed by project key."
  value = {
    for project_key, identity in module.project_deploy_identity :
    project_key => identity.service_user_name
  }
}

output "project_deploy_roles" {
  description = "Existing project DEPLOY roles bound to PROD deployment service users."
  value = {
    for project_key, identity in module.project_deploy_identity :
    project_key => identity.role_name
  }
}

output "project_deploy_oidc_subjects" {
  description = "GitHub OIDC subjects trusted by PROD project deployment service users."
  value = {
    for project_key, identity in module.project_deploy_identity :
    project_key => identity.oidc_subject
  }
}

output "project_ci_service_users" {
  description = "Project CI Snowflake SERVICE users keyed by project key."
  value = {
    for project_key, identity in module.project_ci_identity :
    project_key => identity.service_user_name
  }
}

output "project_ci_roles" {
  description = "Existing machine-only CI roles bound to project service users."
  value = {
    for project_key, identity in module.project_ci_identity :
    project_key => identity.role_name
  }
}

output "project_ci_oidc_subjects" {
  description = "GitHub OIDC subjects trusted by project CI service users."
  value = {
    for project_key, identity in module.project_ci_identity :
    project_key => identity.oidc_subject
  }
}

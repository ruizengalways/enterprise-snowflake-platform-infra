output "service_user_name" {
  value = module.workload_identity.service_user_name
}

output "role_name" {
  value = module.workload_identity.role_name
}

output "oidc_subject" {
  value = module.workload_identity.oidc_subject
}

output "oidc_audience" {
  value = module.workload_identity.oidc_audience
}

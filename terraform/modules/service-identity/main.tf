resource "snowflake_service_user" "this" {
  name                           = var.service_user_name
  default_role                   = var.role_name
  default_secondary_roles_option = "NONE"
  disabled                       = "false"
  comment                        = var.comment

  default_workload_identity {
    oidc {
      issuer             = var.oidc_issuer
      subject            = var.oidc_subject
      oidc_audience_list = [var.oidc_audience]
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_grant_account_role" "to_service_user" {
  role_name = var.role_name
  user_name = snowflake_service_user.this.name
}

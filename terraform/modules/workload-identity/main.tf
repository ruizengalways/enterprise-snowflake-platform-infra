resource "snowflake_account_role" "terraform" {
  name    = var.role_name
  comment = "Routine Terraform automation role; managed by enterprise-snowflake-platform-infra identity bootstrap."

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_grant_privileges_to_account_role" "terraform_account" {
  privileges        = var.account_privileges
  account_role_name = snowflake_account_role.terraform.name
  on_account        = true
}

# Keep the machine role reachable from the system-role hierarchy without
# expanding SYSADMIN. ACCOUNTADMIN already has the equivalent administrative
# authority and remains restricted to bootstrap/emergency use.
resource "snowflake_grant_account_role" "terraform_to_accountadmin" {
  role_name        = snowflake_account_role.terraform.name
  parent_role_name = "ACCOUNTADMIN"
}

resource "snowflake_service_user" "terraform" {
  name                           = var.service_user_name
  default_role                   = snowflake_account_role.terraform.name
  default_secondary_roles_option = "NONE"
  disabled                       = "false"
  comment                        = "GitHub Actions workload identity for Terraform; no password or private key."

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

resource "snowflake_grant_account_role" "terraform_to_service_user" {
  role_name = snowflake_account_role.terraform.name
  user_name = snowflake_service_user.terraform.name
}

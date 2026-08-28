locals {
  config = yamldecode(file("${path.root}/../../../config/organization.yml"))
}

resource "snowflake_account" "environment" {
  provider = snowflake.orgadmin
  for_each = local.config.accounts

  name                 = each.value.name
  admin_name           = var.initial_admin_name
  admin_rsa_public_key = var.initial_admin_rsa_public_key
  admin_user_type      = "SERVICE"
  email                = var.initial_admin_email
  edition              = each.value.edition
  is_org_admin         = tostring(each.value.is_org_admin)
  grace_period_in_days = each.value.grace_period_days
  comment              = "${upper(each.key)} account for the Enterprise Snowflake Platform; managed by organization bootstrap Terraform."

  # Deleting an environment account is never an ordinary Terraform operation.
  # Any retirement requires an explicit architecture/operations decision first.
  lifecycle {
    prevent_destroy = true
  }
}

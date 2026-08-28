terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = ">= 2.19.0, < 3.0.0"

      # Historical alias names remain module-internal for compatibility. Root
      # stacks map these lifecycle surfaces to their least-privilege routine
      # Terraform provider, not to Snowflake system roles.
      configuration_aliases = [
        snowflake.securityadmin,
        snowflake.sysadmin,
      ]
    }
  }
}

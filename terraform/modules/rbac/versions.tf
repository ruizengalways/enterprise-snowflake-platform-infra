terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = ">= 2.19.0, < 3.0.0"

      configuration_aliases = [
        snowflake.objects,
        snowflake.security,
      ]
    }
  }
}

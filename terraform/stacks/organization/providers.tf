# Organization bootstrap is deliberately isolated from normal DEV/UAT/PROD
# account administration. Authentication/account context is supplied externally.
provider "snowflake" {
  alias = "orgadmin"
  role  = "ORGADMIN"
}

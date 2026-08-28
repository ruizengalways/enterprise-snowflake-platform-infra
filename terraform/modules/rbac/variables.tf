variable "project_codes" {
  description = "Project codes used in account/database role names, for example HEALTH and TRANSPORT."
  type        = set(string)
}

variable "database_projects" {
  description = "Mapping of analytics database name to the single owning data-product/project code."
  type        = map(string)
}

variable "stable_schemas_by_database" {
  description = "Stable schemas by analytics database. Personal and PR schemas are intentionally excluded."
  type        = map(set(string))
}

variable "grant_developer_write" {
  description = "Whether project developer account roles receive the WRITE database role in this account. True in DEV; false in UAT/PROD."
  type        = bool
}

variable "warehouse_grants" {
  description = "Warehouse USAGE grants keyed by account-role name. Role hierarchy provides inherited access."
  type        = map(set(string))
  default     = {}
}

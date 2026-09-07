variable "recovery_warehouse_grants" {
  description = "Transform warehouses usable by each project recovery role. Keys are project codes."
  type        = map(set(string))
  default     = {}
}

locals {
  pod_security_group_id = "sg-0a2c0d47be0125ba9"
  lb_security_group_id  = "sg-0c1539967e68ded8b"
  service_name          = "zion"
  short_env             = "stg"
  helix_entity_ref      = "component:zion"
  default_tags ={
    tags = {
      "helix.engtools.net_entity-ref" = "component:zion"
      "Costing_Family"                = "APEX-FOUNDATIONS-SWAT"
      "App_Name"                      = "zion"
    }
  }
}

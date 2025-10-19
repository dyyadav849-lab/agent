locals {
  pod_security_group_id = "sg-090d34c4838f83851"
  lb_security_group_id  = "sg-04d082086a3f78249"
  service_name          = "zion"
  short_env             = "prd"
  helix_entity_ref      = "component:zion"
  default_tags ={
    tags = {
      "helix.engtools.net_entity-ref" = "component:zion"
      "Costing_Family"                = "APEX-FOUNDATIONS-SWAT"
      "App_Name"                      = "zion"
    }
  }
}

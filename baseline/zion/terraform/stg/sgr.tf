# Allow HTTP health-check by Kubelet
resource "aws_security_group_rule" "ingress_stg_eks_common_to_zion_k8s_port_8000" {
  description              = "Kubelet HTTP health check on service"
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = "sg-0e00540d0497e5a4a" # stg-eks-common
  security_group_id        = local.pod_security_group_id
}

# Allow OneVPN CIDR to access ALB ingress
# since the same SG will be attached to the ingress ALB too
resource "aws_security_group_rule" "ingress_onevpn_cidr_to_zion_alb_ingress_port_443_to_445" {
  description       = "OneVPN CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 443
  to_port           = 445
  protocol          = "tcp"
  cidr_blocks       = ["10.6.24.0/22", "10.28.0.0/16"] # OneVPN CIDR
  security_group_id = local.lb_security_group_id
}

# Allow OneVPN CIDR to access ALB ingress
# since the same SG will be attached to the ingress ALB too
resource "aws_security_group_rule" "ingress_onevpn_cidr_to_zion_alb_ingress_port_80" {
  description       = "OneVPN CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["10.6.24.0/22", "10.28.0.0/16"] # OneVPN CIDR
  security_group_id = local.lb_security_group_id
}

# Allow Helix to access zion
resource "aws_security_group_rule" "ingress_helix_cidr_to_mesh_east_alb_ingress_port_80_zion" {
  description       = "Helix CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["10.195.188.0/23"]
  security_group_id = local.lb_security_group_id
}

# Allow Helix to access zion
resource "aws_security_group_rule" "ingress_helix_cidr_to_mesh_east_alb_ingress_port_443_zion" {
  description       = "Helix CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.195.188.0/23"]
  security_group_id = local.lb_security_group_id
}

# Allow ti-support-bot to access ALB ingress
resource "aws_security_group_rule" "ingress_ti_support_bot_to_zion_https" {
  description              = "TI Suport Bot access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "011014824127/sg-0fe0d6908b461231c"
  security_group_id        = local.lb_security_group_id
}


# Allow kinabalu to access ALB ingress
resource "aws_security_group_rule" "ingress_kinabalu_to_zion_https" {
  description              = "Kinabalu access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "011014824127/sg-0178b85718d3ee63d"
  security_group_id        = local.lb_security_group_id
}

# Allow fire-service-query to access ALB ingress
resource "aws_security_group_rule" "ingress_fire-service-query_to_zion_https" {
  description              = "fire-service-query access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "011014824127/sg-0b7250ef863695d2f"
  security_group_id        = local.lb_security_group_id
}

# Allow FLIP ai-proxy to access ALB ingress
resource "aws_security_group_rule" "ingress_ai_proxy_to_zion_https" {
  description              = "ai-proxy access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "011014824127/sg-0360ad5af806ef527"
  security_group_id        = local.lb_security_group_id
}

# Allow AIHome-be proxy to access ALB ingress
resource "aws_security_group_rule" "ingress_aihome_be_proxy_to_zion_https" {
  description              = "aihome-be-proxy access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "011014824127/sg-0fa0a4b9dacfa2190"
  security_group_id        = local.lb_security_group_id
}

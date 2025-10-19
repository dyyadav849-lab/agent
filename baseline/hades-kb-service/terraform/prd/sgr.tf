# Allow HTTP health-check by Kubelet

resource "aws_security_group_rule" "ingress_prd_eks_common_to_hades-kb-service_k8s_port_8088" {
  description              = "Kubelet HTTP health check on service"
  type                     = "ingress"
  from_port                = 8088
  to_port                  = 8088
  protocol                 = "tcp"
  source_security_group_id = "sg-008fe687ed45486eb" # prd-eks-common
  security_group_id        = local.pod_security_group_id
}


# Allow OneVPN CIDR to access ALB ingress
resource "aws_security_group_rule" "ingress_onevpn_cidr_to_hades-kb-service_alb_ingress_port_443_to_445" {
  description       = "OneVPN CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 443
  to_port           = 445
  protocol          = "tcp"
  cidr_blocks       = ["10.6.24.0/22", "10.28.0.0/16"]  #OneVPN CIDR
  security_group_id = local.lb_security_group_id
}

# Allow OneVPN CIDR to access ALB ingress
resource "aws_security_group_rule" "ingress_onevpn_cidr_to_hades-kb-service_alb_ingress_port_80" {
  description       = "OneVPN CIDR access for ALB ingress"
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["10.6.24.0/22", "10.28.0.0/16"]  #OneVPN CIDR
  security_group_id = local.lb_security_group_id
}

# Allow ti-support-bot to access ALB ingress
resource "aws_security_group_rule" "ingress_ti_support_bot_to_hades_https" {
  description              = "TI Support Bot access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "799957839491/sg-05b3712405229bb85"
  security_group_id        = local.lb_security_group_id
}

# Allow ti-support-bot to access ALB ingress
resource "aws_security_group_rule" "ingress_ti_support_bot_to_hades_http" {
  description              = "TI Support Bot access for ALB ingress"
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = "799957839491/sg-05b3712405229bb85"
  security_group_id        = local.lb_security_group_id
}

# Allow aihomebe to access ALB ingress
resource "aws_security_group_rule" "ingress_aihomebe_to_hades_https" {
  description              = "aihomebe access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "799957839491/sg-094ed7c673d44554e"
  security_group_id        = local.lb_security_group_id
}

# Allow zion to access ALB ingress
resource "aws_security_group_rule" "ingress_zion_to_hades_https" {
  description              = "Zion access for ALB ingress"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = "799957839491/sg-090d34c4838f83851"
  security_group_id        = local.lb_security_group_id
}

# Allow zion to access ALB ingress
resource "aws_security_group_rule" "ingress_zion_to_hades_http" {
  description              = "Zion access for ALB ingress"
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = "799957839491/sg-090d34c4838f83851"
  security_group_id        = local.lb_security_group_id
}

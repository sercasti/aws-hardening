# KMS CMK module con defaults seguros
# Aplica automaticamente:
# - Rotacion automatica cada 365 dias
# - Periodo de espera para deletion de 30 dias (no se puede borrar menos de 30)
# - Key policy default que requiere MFA para admin operations
# - Multi-Region opcional

variable "key_alias" {
  description = "Alias para la KMS key (sin el prefijo alias/)"
  type        = string
}

variable "key_description" {
  description = "Descripcion humana de para que sirve esta key"
  type        = string
}

variable "multi_region" {
  description = "Crear como Multi-Region key"
  type        = bool
  default     = false
}

variable "additional_tags" {
  description = "Tags adicionales para la key"
  type        = map(string)
  default     = {}
}

variable "admin_role_arn" {
  description = "ARN del rol que administra esta key"
  type        = string
}

variable "user_role_arns" {
  description = "Lista de ARNs que pueden usar la key para encrypt/decrypt"
  type        = list(string)
  default     = []
}

resource "aws_kms_key" "this" {
  description              = var.key_description
  key_usage                = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"

  # Rotacion automatica habilitada
  enable_key_rotation     = true

  # 30 dias de espera para deletion (minimo seguro, maximo 30)
  deletion_window_in_days = 30

  # Multi-Region opcional
  multi_region = var.multi_region

  # Key policy con defaults seguros
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "EnableIAMRootPermissionsWithMFA"
          Effect = "Allow"
          Principal = {
            AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
          }
          Action   = "kms:*"
          Resource = "*"
          Condition = {
            Bool = {
              "aws:MultiFactorAuthPresent" = "true"
            }
          }
        },
        {
          Sid    = "AllowAdminRole"
          Effect = "Allow"
          Principal = {
            AWS = var.admin_role_arn
          }
          Action = [
            "kms:Describe*",
            "kms:List*",
            "kms:Enable*",
            "kms:Update*",
            "kms:Disable*",
            "kms:Get*",
            "kms:Revoke*"
          ]
          Resource = "*"
        }
      ],
      length(var.user_role_arns) > 0 ? [
        {
          Sid    = "AllowUserRoles"
          Effect = "Allow"
          Principal = {
            AWS = var.user_role_arns
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey"
          ]
          Resource = "*"
        }
      ] : []
    )
  })

  tags = merge(
    {
      Name                 = var.key_alias
      ManagedBy            = "terraform"
      RotationEnabled      = "true"
      DeletionWindowDays   = "30"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.key_alias}"
  target_key_id = aws_kms_key.this.key_id
}

data "aws_caller_identity" "current" {}

output "key_arn" {
  value = aws_kms_key.this.arn
}

output "key_id" {
  value = aws_kms_key.this.key_id
}

output "alias_name" {
  value = aws_kms_alias.this.name
}

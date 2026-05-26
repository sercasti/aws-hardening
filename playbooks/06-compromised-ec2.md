# Playbook 06: EC2 comprometida

> Una instancia EC2 muestra signos de compromiso: malware, conexiones outbound sospechosas, mining, behavior anómalo del proceso. Este playbook minimiza el blast radius sin destruir evidencia.

## Trigger

- **GuardDuty finding** `Backdoor:EC2/*`, `CryptoCurrency:EC2/*`, `UnauthorizedAccess:EC2/*`, `Trojan:EC2/*`.
- **Alerta de antivirus/EDR** corriendo dentro de la instancia.
- **VPC Flow Logs anomaly**: conexiones a IPs maliciosas conocidas.
- **CloudWatch metric anomaly**: CPU/network sostenido fuera del baseline.
- Reporte humano: "el proceso X está corriendo y no debería".

## Severity

- **Critical** si la instancia maneja data sensible, está en producción, o el compromise es activo.
- **High** si es staging/test pero con acceso a recursos prod (cross-account roles, peering).
- **Medium** si es sandbox/dev aislado.

## SLA

- **Detection a Containment**: 1 hora.
- **Containment a Eradication**: 4 horas.
- **Recovery**: variable.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (10 minutos)

**A. Confirmar la instancia y su rol.**

```bash
INSTANCE_ID="i-xxxxxxxxxxx"

aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,LaunchTime,Tags,IamInstanceProfile.Arn,VpcId,SubnetId,SecurityGroups]'
```

Mirá:

- **Tags**: ¿es prod/staging/dev?
- **InstanceProfile**: ¿qué rol AWS tiene esta instancia?
- **VPC/Subnet**: ¿está en una VPC sensible?
- **Security Groups**: ¿qué tiene permitido?

**B. Capturar memoria/proceso (si el EDR lo permite).**

Si tenés AWS Systems Manager Session Manager:

```bash
aws ssm start-session --target $INSTANCE_ID

# Dentro de la sesión:
ps auxf
netstat -anp | grep ESTABLISHED
who
last -20
ls -la /tmp /var/tmp
crontab -l
sudo lsof -i -n
```

Documentar lo que ves. NO matar procesos todavía.

**C. Pedir un snapshot de memoria si es Critical.**

Para análisis forensic profundo, el snapshot del volumen no alcanza. Necesitás memory dump. Tools como AWS Incident Response Service o EDR externo (CrowdStrike, SentinelOne) capturan memoria. Si no tenés, el snapshot de volumen es lo mejor que podés.

### 2. Containment (15 minutos)

**A. Aislar la instancia (NO terminate).**

```bash
# Crear un security group "quarantine" con cero egress
QUARANTINE_SG=$(aws ec2 create-security-group \
  --group-name quarantine-$(date +%s) \
  --description "IR quarantine" \
  --vpc-id [VPC_ID] \
  --query 'GroupId' --output text)

# Asignar el security group (reemplaza los actuales)
aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --groups $QUARANTINE_SG
```

La instancia sigue arriba (proceso, memoria intacta) pero no puede hablar con nada.

**B. Capturar snapshots para forensics.**

```bash
# Identificar los volúmenes
VOLUMES=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[].Instances[].BlockDeviceMappings[].Ebs.VolumeId' --output text)

# Snapshot cada uno
for vol in $VOLUMES; do
  aws ec2 create-snapshot \
    --volume-id $vol \
    --description "IR-snapshot-$(date +%Y%m%d-%H%M%S)" \
    --tag-specifications "ResourceType=snapshot,Tags=[{Key=incident,Value=$(date +%s)},{Key=do-not-delete,Value=true}]"
done
```

**C. Revocar credenciales temporales del instance profile.**

Si la instancia tiene un IAM role asociado, sus credenciales temporales pueden estar afuera (el atacante las exfiltró). Revocar:

```bash
# Identificar el role
ROLE_NAME=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[].Instances[].IamInstanceProfile.Arn' --output text | awk -F/ '{print $NF}')

# Aplicar policy de revocación a sesiones existentes
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name AWSRevokeOlderSessions \
  --policy-document file://revoke-sessions.json

# Contenido de revoke-sessions.json:
# {
#   "Version": "2012-10-17",
#   "Statement": [{
#     "Effect": "Deny",
#     "Action": "*",
#     "Resource": "*",
#     "Condition": {
#       "DateLessThan": {
#         "aws:TokenIssueTime": "[NOW_UTC_ISO]"
#       }
#     }
#   }]
# }
```

Esta policy invalida cualquier sesión IAM temporal que haya sido emitida ANTES de este momento. Sesiones nuevas (de workloads legítimos) siguen funcionando.

### 3. Eradication (30 a 90 minutos)

**A. Análisis del snapshot de volumen.**

Levantar una instancia forensic separada, attach el snapshot, montar como read-only, analizar:

```bash
# En la instancia forensic (separada):
sudo mount -o ro /dev/xvdf1 /mnt/forensic

# Buscar IOCs típicos:
sudo find /mnt/forensic -name "*.sh" -mtime -7
sudo find /mnt/forensic -path "*/.ssh/authorized_keys" -mtime -7
sudo find /mnt/forensic -name "minerd*" -o -name "xmrig*"
sudo cat /mnt/forensic/var/log/auth.log | grep -i "sudo\|fail\|invalid"
sudo cat /mnt/forensic/etc/passwd | grep -v "/sbin/nologin"
sudo cat /mnt/forensic/root/.bash_history 2>/dev/null
```

**B. Identificar el vector inicial.**

Preguntas a responder:

- ¿Cómo entró el atacante? (SSH brute force, exploit a aplicación, supply chain, etc.)
- ¿Cuándo entró? (timestamps)
- ¿Qué hizo dentro? (mining, exfil, reconnaissance, lateral movement)
- ¿Sigue dentro? (la instancia aislada o vía credenciales que extrajo)

**C. Buscar persistence.**

- **AuthorizedKeys** modificados.
- **Crontabs** con tareas sospechosas.
- **systemd services** instalados.
- **Binarios sospechosos** en `/tmp`, `/var/tmp`, `/dev/shm`.
- **IAM credentials** robadas (el atacante las usó en otra cuenta).

**D. Si la instancia tenía role con acceso a otros recursos, auditar esos recursos.**

```bash
# Listar policies del role
aws iam list-attached-role-policies --role-name $ROLE_NAME
aws iam list-role-policies --role-name $ROLE_NAME

# Para cada permiso, buscar uso en CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=$ROLE_NAME \
  --start-time '[INCIDENT_START]' \
  --max-items 1000
```

### 4. Recovery

**A. Terminate la instancia comprometida.**

Una vez completado el forensics:

```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

**B. Reemplazar la instancia.**

- Desde una AMI golden (no la que tenía la instancia comprometida).
- Con el patch que cierra el vector inicial.
- Con tags consistentes con la org.
- Con monitoring inmediato.

**C. Restore data si era necesario.**

Si la instancia tenía data efímera que se perdió, restore desde backup. Si era data persistente en EBS y el volume está limpio, attach a la nueva instancia.

**D. Comunicación.**

- Al equipo dueño del servicio.
- A SecOps/SRE: post-mortem agendado.
- Si hubo exfil confirmada: compliance/legal.

### 5. Post-mortem (1 semana)

Énfasis especial en:

1. **Vector inicial.** Qué exactamente permitió la entrada. Esto define los action items.
2. **Tiempo dentro.** Cuánto estuvo el atacante en la instancia antes de detectar.
3. **Persistence found.** Si dejó backdoors, todos los hallazgos.
4. **Lateral movement.** Si pasó a otras instancias/cuentas.
5. **Action items.**
   - Patch del CVE o config issue que permitió la entrada.
   - Mejora del detection (¿GuardDuty estaba habilitado? ¿el EDR estaba corriendo?).
   - Hardening de imagen base.
   - Reducción del scope del IAM role (instance profile).

## Anti-patterns

- ❌ **Terminate la instancia antes del forensics.** Pierdes evidencia de cómo entraron y qué hicieron.
- ❌ **Login a la instancia con SSH user normal post-compromise.** Si el atacante tiene un keylogger, comprometés tu propia credencial.
- ❌ **Asumir que es solo mining sin investigar exfil.** Atacantes sofisticados usan mining como cover.
- ❌ **Restaurar desde el mismo snapshot que se comprometió.** Si el malware está en `/etc/cron.d/`, va a volver.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que recibe `INSTANCE_ID` y hace los pasos de captura + isolation:

```bash
./scripts/isolate-instance.sh i-xxxxxxxxxxx
# Output: snapshot IDs, quarantine SG ID, credentials revoked
```

### Fase 3: Semi-automático

EventBridge sobre GuardDuty finding con tipo `Backdoor:EC2/*` o `CryptoCurrency:EC2/*`:

```
Trigger: GuardDuty finding
   ↓
Lambda 1: Snapshot volumes
   ↓
Lambda 2: Apply quarantine SG
   ↓
Lambda 3: Revoke role sessions
   ↓
Lambda 4: Notify on-call with details + evidence locations
   ↓
Human: investiga, ejecuta eradication
```

### Fase 4: Automático

No recomendado. Las decisiones de "esta instancia es legítima pero comprometida" vs "esta instancia no debería existir, fue creada por el atacante" requieren contexto.

## Métricas

- **Time to isolate**: tiempo entre finding y quarantine SG aplicada.
- **Time to forensics**: tiempo entre isolate y análisis completado.
- **Time to recovery**: tiempo entre detection y servicio operacional otra vez.
- **Lateral movement detected**: número de otras instancias/cuentas afectadas.

## Recursos

- [AWS Incident Response (free tier)](https://aws.amazon.com/security/incident-response/)
- [GuardDuty finding types](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html)
- [SANS Forensics docs](https://www.sans.org/blog/digital-forensics-and-incident-response/)
- [AWS EC2 forensics workshop](https://github.com/aws-samples/aws-incident-response-runbooks)

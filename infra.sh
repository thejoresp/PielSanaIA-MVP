
######################## LABORATORIO IFTS 11 ##################################
#
###############################################################################
## Tratamiento de variables de entrada
###############################################################################
AWS_VPC_CIDR_BLOCK=10.22.0.0/16
AWS_Subred_CIDR_BLOCK=10.22.115.0/24
AWS_IP_UbuntuServer=10.22.115.100
AWS_Proyecto=PielSanaIA

echo "######################################################################"
echo "Creación de una VPC, subredes, internet gateway y tabla de rutas."
echo "Además creará una instancia EC2 Ubuntu Server 22.04 con IPs elásticas en AWS con AWS CLI"
echo "Se van a crear con los siguientes valores:"
echo "AWS_VPC_CIDR_BLOCK:    " $AWS_VPC_CIDR_BLOCK
echo "AWS_Subred_CIDR_BLOCK: " $AWS_Subred_CIDR_BLOCK
echo "AWS_IP_UbuntuServer:   " $AWS_IP_UbuntuServer
echo "AWS_Proyecto:          " $AWS_Proyecto
echo "######################################################################"
###############################################################################
## Crear una VPC (Virtual Private Cloud) con su etiqueta
## La VPC tendrá un bloque IPv4 proporcionado por el usuario y uno IPv6 de AWS ???
echo "############## Crear VPC, Subred, Rutas, Gateway #####################"
echo "######################################################################"
echo "Creando VPC..."

AWS_ID_VPC=$(aws ec2 create-vpc \
  --cidr-block $AWS_VPC_CIDR_BLOCK \
  --amazon-provided-ipv6-cidr-block \
  --tag-specification ResourceType=vpc,Tags=[{Key=Name,Value=$AWS_Proyecto-vpc}] \
  --query 'Vpc.{VpcId:VpcId}' \
  --output text)

## Habilitar los nombres DNS para la VPC
aws ec2 modify-vpc-attribute \
  --vpc-id $AWS_ID_VPC \
  --enable-dns-hostnames "{\"Value\":true}"

## Crear una subred publica con su etiqueta
echo "Creando Subred..."
AWS_ID_SubredPublica=$(aws ec2 create-subnet \
  --vpc-id $AWS_ID_VPC --cidr-block $AWS_Subred_CIDR_BLOCK \
  --availability-zone us-east-1a \
  --tag-specifications ResourceType=subnet,Tags=[{Key=Name,Value=$AWS_Proyecto-subred-publica}] \
  --query 'Subnet.{SubnetId:SubnetId}' \
  --output text)

## Habilitar la asignación automática de IPs públicas en la subred pública
aws ec2 modify-subnet-attribute \
  --subnet-id $AWS_ID_SubredPublica \
  --map-public-ip-on-launch

## Crear un Internet Gateway (Puerta de enlace) con su etiqueta
echo "Creando Internet Gateway..."
AWS_ID_InternetGateway=$(aws ec2 create-internet-gateway \
  --tag-specifications ResourceType=internet-gateway,Tags=[{Key=Name,Value=$AWS_Proyecto-igw}] \
  --query 'InternetGateway.{InternetGatewayId:InternetGatewayId}' \
  --output text)

## Asignar el Internet gateway a la VPC
aws ec2 attach-internet-gateway \
--vpc-id $AWS_ID_VPC \
--internet-gateway-id $AWS_ID_InternetGateway

## Crear una tabla de rutas
echo "Creando tabla de rutas..."
AWS_ID_TablaRutas=$(aws ec2 create-route-table \
--vpc-id $AWS_ID_VPC \
--query 'RouteTable.{RouteTableId:RouteTableId}' \
--output text )

## Crear la ruta por defecto a la puerta de enlace IPv4 (Internet Gateway)
echo "     Ruta por defecto IPv4 0.0.0.0/0..."
aws ec2 create-route \
  --route-table-id $AWS_ID_TablaRutas \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $AWS_ID_InternetGateway

## Crear la ruta por defecto a la puerta de enlace IPv4 (Internet Gateway)
echo "     Ruta por defecto IPv6 ::/0..."
aws ec2 create-route --route-table-id  $AWS_ID_TablaRutas \
  --destination-ipv6-cidr-block ::/0 \
  --gateway-id $AWS_ID_InternetGateway

## Asociar la subred pública con la tabla de rutas
AWS_ROUTE_TABLE_ASSOID=$(aws ec2 associate-route-table  \
  --subnet-id $AWS_ID_SubredPublica \
  --route-table-id $AWS_ID_TablaRutas \
  --output text)

## Añadir etiqueta a la ruta por defecto
AWS_DEFAULT_ROUTE_TABLE_ID=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$AWS_ID_VPC" \
  --query 'RouteTables[?Associations[0].Main != `flase`].RouteTableId' \
  --output text) &&
aws ec2 create-tags \
--resources $AWS_DEFAULT_ROUTE_TABLE_ID \
--tags "Key=Name,Value=$AWS_Proyecto ruta por defecto"

## Añadir etiquetas a la tabla de rutas
aws ec2 create-tags \
--resources $AWS_ID_TablaRutas \
--tags "Key=Name,Value=$AWS_Proyecto-rtb-public"


###############################################################################
####################       UBUNTU SERVER     ##################################
###############################################################################
## Crear un grupo de seguridad Ubuntu Server
echo "########################### Ubuntu Server ############################"
echo "######################################################################"
echo "Creando grupo de seguridad Ubuntu Server..."
AWS_ID_GrupoSeguridad_Ubuntu=$(aws ec2 create-security-group \
  --vpc-id $AWS_ID_VPC \
  --group-name $AWS_Proyecto-us-sg \
  --description "$AWS_Proyecto-us-sg" \
  --output text)

echo "ID Grupo de seguridad de ubuntu: " $AWS_ID_GrupoSeguridad_Ubuntu

echo "Añadiendo reglas de seguridad al grupo de seguridad Ubuntu Server..."
aws ec2 authorize-security-group-ingress \
  --group-id $AWS_ID_GrupoSeguridad_Ubuntu \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow SSH"}]}]'

aws ec2 authorize-security-group-ingress \
  --group-id $AWS_ID_GrupoSeguridad_Ubuntu \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow HTTP"}]}]'

aws ec2 authorize-security-group-ingress \
  --group-id $AWS_ID_GrupoSeguridad_Ubuntu \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 53, "ToPort": 53, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow DNS(TCP)"}]}]'

aws ec2 authorize-security-group-ingress \
  --group-id $AWS_ID_GrupoSeguridad_Ubuntu \
  --ip-permissions '[{"IpProtocol": "UDP", "FromPort": 53, "ToPort": 53, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Allow DNS(UDP)"}]}]'

aws ec2 authorize-security-group-ingress \
  --group-id $AWS_ID_GrupoSeguridad_Ubuntu \
  --protocol tcp --port 8080 \
  --cidr 0.0.0.0/0 \
  --description "Allow HTTP on port 8080"



## Añadirle etiqueta al grupo de seguridad
echo "Añadiendo etiqueta al grupo de seguridad Ubuntu Server..."
aws ec2 create-tags \
--resources $AWS_ID_GrupoSeguridad_Ubuntu \
--tags "Key=Name,Value=$AWS_Proyecto-us-sg" 

###############################################################################
## Crear una instancia EC2  (con una imagen de ubuntu 22.04 del 04/07/2022)
echo ""
echo "Creando instancia EC2 Ubuntu  ##################################"
AWS_AMI_Ubuntu_ID=ami-04b70fa74e45c3917
AWS_EC2_INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AWS_AMI_Ubuntu_ID \
  --instance-type t2.micro \
  --key-name vockey \
  --monitoring "Enabled=false" \
  --security-group-ids $AWS_ID_GrupoSeguridad_Ubuntu \
  --subnet-id $AWS_ID_SubredPublica \
  --user-data file://dockerUbuntu.txt \
  --private-ip-address $AWS_IP_UbuntuServer \
  --tag-specifications ResourceType=instance,Tags=[{Key=Name,Value=pielsanaia}] \
  --query 'Instances[0].InstanceId' \
  --output text)

#echo $AWS_EC2_INSTANCE_ID
###############################################################################
## Crear IP Estatica para la instancia Ubuntu. (IP elastica)
echo "Creando IP elastica Ubuntu"
AWS_IP_Fija_UbuntuServer=$(aws ec2 allocate-address --output text)
echo $AWS_IP_Fija_UbuntuServer 

## Recuperar AllocationId de la IP elastica
AWS_IP_Fija_UbuntuServer_AllocationId=$(echo $AWS_IP_Fija_UbuntuServer | awk '{print $1}')
echo $AWS_IP_Fija_UbuntuServer_AllocationId

## Añadirle etiqueta a la ip elástica de Ubuntu
aws ec2 create-tags \
--resources $AWS_IP_Fija_UbuntuServer_AllocationId \
--tags Key=Name,Value=$AWS_Proyecto-us-ip

###############################################################################
## Asociar la ip elastica a la instancia Ubuntu
echo "Esperando a que la instancia esté disponible para asociar la IP elastica"
sleep 100
aws ec2 associate-address --instance-id $AWS_EC2_INSTANCE_ID --allocation-id $AWS_IP_Fija_UbuntuServer_AllocationId

###############################################################################
## Mostrar las ips publicas de las instancias
echo "Mostrando las ips publicas de las instancias"
AWS_EC2_INSTANCE_PUBLIC_IP=$(aws ec2 describe-instances \
--query "Reservations[*].Instances[*].PublicIpAddress" \
--output=text) &&
echo $AWS_EC2_INSTANCE_PUBLIC_IP
###############################################################################

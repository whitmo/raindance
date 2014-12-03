#!/bin/bash
set -e

cat > ./inventory.ini <<EOF
[local]
localhost

[blbox]

EOF

cat > ./vars/run-vars.yml <<EOF
---
rel: $1
aaki: ${AWS_ACCESS_KEY}
asak: ${AWS_SECRET_KEY}
instance_id: ${2}
EOF


CMD="ansible-playbook --private-key=/home/ubuntu/.juju/ssh/juju_id_rsa -vv -i ./inventory.ini  ./aws.yml"

echo $CMD
$CMD

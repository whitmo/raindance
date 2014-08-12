#!/bin/bash
set -e
cat > ./inventory.ini <<EOF
[blbox]
$2
EOF

cat ./inventory.ini

ansible-playbook -vv -e "rel=$1" -e "aaki=${AWS_ACCESS_KEY}" -e "asak=${AWS_SECRET_ACCESS_KEY}"  -i ./inventory.ini $3  ./boshlite.yml

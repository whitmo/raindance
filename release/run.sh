#!/bin/bash
set -e
cat > ./inventory.ini <<EOF
[blbox]
$2
EOF

cat ./inventory.ini

AMI=`curl -s https://bosh-lite-build-artifacts.s3.amazonaws.com/ami/bosh-lite-ami.list |tail -1`

ansible-playbook -vv -e "rel=$1" -e "aaki=${AWS_ACCESS_KEY}" -e "asak=${AWS_SECRET_ACCESS_KEY}"  -i ./inventory.ini $3  ./boshlite.yml

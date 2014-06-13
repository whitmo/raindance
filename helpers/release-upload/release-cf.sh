bosh download public stemcell  bosh-stemcell-3-warden-boshlite-ubuntu-trusty-go_agent.tgz
bosh upload stemcell  bosh-stemcell-3-warden-boshlite-ubuntu-trusty-go_agent.tgz
bosh create release --force
bosh upload release /opt/cf-release/dev_releases/cf-172.3-dev.yml

bosh deploy
bosh export compiled_packages cf/172+dev.1 bosh-warden-boshlite-ubuntu-trusty-go_agent/3 ./out


# 1.2583.0
# 1.2559.0

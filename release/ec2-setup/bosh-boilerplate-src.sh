export RBENV_SHELL="bash"
export RBENV_ROOT="/opt/rbenv"
export PATH=/opt/rbenv/shims:/opt/rbenv/bin:/opt/rbenv/bin/rbenv:$PATH
eval "$(rbenv init -)"
export CF_RELEASE_DIR=/opt/cf-release
export BOSH_USER=admin
export BOSH_PASSWORD=admin
. /opt/packages/bin/activate
export AWS_ACCESS_KEY_ID={{aaki}}
export AWS_SECRET_ACCESS_KEY={{asak}}

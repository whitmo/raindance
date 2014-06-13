set -e
apt-get install -y git
apt-get install -y ruby-dev
apt-get install -y unzip
gem install bundler
mkdir -p /opt/
git clone https://github.com/cloudfoundry/bosh-lite.git /opt/boshlite
pushd `pwd`
cd /opt/bosh-lite
# edit .ruby-version to match system
bundle

#@@ target and login bs
# set up release
cd /usr/bin
curl https://github.com/cloudfoundry-incubator/spiff/releases/download/v1.0/spiff_linux_amd64.zip | unzip
popd

git clone https://github.com/cloudfoundry/cf-release.git /opt/cf-release
cd /opt/cf-release
./update

mkdir -p /opt/cp-cache

# make manifest
## sub lucid for trusty

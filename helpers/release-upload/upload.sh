set -e
. /vagrant/keys.sh
cp ./$2/compiled_packages.MF ./$2/compiled_packages/blobs/index.json
pushd . && cd "$2"/compiled_packages/blobs/
/opt/out/paraput.py --put=add --grant=public-read --bucket="${1}" --prefix="$2" ./
/opt/out/upload-index.py $2
popd

# Possible pitfalls
  - exported compiled packages may not include all desired packages
    (CF Runtime Team does not deploy all jobs inside cf-release)

# s3 up

gvm : https://github.com/moovweb/gvmeb/gvm
gvm install go1.3
gvm use 1.3

go get github.com/rlmcpherson/s3gof3r

https://gowalker.org/github.com/rlmcpherson/s3gof3r

 - requires env vars in key.sh
 

# New Pipeline

## upload

 - s3 bucket with
   - {release name}-{release version}-{shorten sha1}.tar.gz

 - provision aws node
   - clone cf-release, checkout {sha1}
   - download export, unpack
   - generate new tarballs
     - /{release_name}/{version}/index.yml
       - manifest.cf
     - {job}.tar.gz
       - all compiled packages
       - templates, monit, spec
       - index.json (packages names + sha1)
       - fingerprint
   - upload into s3 location


## download

 - grab /{release_name}/{version}/index.json
 - compare job fingerprints
 - grab jobs that have changed
  - generate new charms 
  - upgrade list for charms 

## 


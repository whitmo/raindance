# Helpers

Most of what's in here now aids with creating package index from a boshlite AWS instance.

## ./ec2-setup

Setting up the ec2 instance for using boshlite to create a release
on that instance.

 - rbenv-source.sh: (source this for access to rbenv ruby)
 - aws-boshlite-setup.sh: more of a draft than script of setup steps (not idempotent)

## ./release-upload

Draft instructions in release-cf.sh

### release utilities:
 - paraput.py: parallel s3 uploader
 - upload-index.py: uploades index.json with correct header and acl
 - upload.sh: a runner for pointing at an unzip export tarball

# TODO

 - Automate this so we can recreate the build box if necessary.
 - prefixing of index for architecture

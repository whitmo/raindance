# Release workflow

Raindance's main function is to create juju consumable
"artifacts". The cli provides basic helpers for this task, but to
actually create a release, we must do several external steps.

The current flow spins up an ec2 instance and install boshlite upon
it, then harvests the resulting packages.

## Setup work instance

We'll need to launch bosh-lite into ec2.

 0. Install vagrant (however you like) and then add plugins and aws
    dummy box:
    ```
    vagrant plugin install vagrant-aws
    vagrant box add dummy https://github.com/mitchellh/vagrant-aws/raw/master/dummy.box
    ```

 0. Create a var.sh and source: ala::
    ```
    export BOSH_AWS_ACCESS_KEY_ID="AWS_ACCESS_KEY"
    export BOSH_AWS_SECRET_ACCESS_KEY="AWS_SECRET_KEY"
    export BOSH_LITE_PRIVATE_KEY='~/.juju/ssh/juju_id_rsa'
    export BOSH_LITE_SECURITY_GROUP='juju-boshlite'
    export BOSH_LITE_KEYPAIR='juju'
    export AWS_ACCESS_KEY=$BOSH_AWS_ACCESS_KEY_ID
    export AWS_SECRET_ACCESS_KEY=$BOSH_AWS_SECRET_ACCESS_KEY
    ```

 0. `git checkout https://github.com/cloudfoundry/bosh-lite.git`

 0. `cd bosh-lite/aws`

 0. `vagrant up --provider=aws`

At the end of the provisioning of the aws instance, it will spit out an address. Copy it for later.

## Running the pipeline

From this repository:

 `./run.sh {release version} {remote address}`

Or for a bit more speed, checkout raindance onto the remote machine,
upload and source your credentials and run:

 `./run.sh {release version} {remote address} --connection=local`


## Pieces parts


Most of what's in here now aids with creating package index from a
boshlite AWS instance.

### ./ec2-setup

Setting up the ec2 instance for using boshlite to create a release
on that instance.

 - rbenv-source.sh: (source this for access to rbenv ruby)
 - aws-boshlite-setup.sh: more of a draft than script of setup steps (not idempotent)

### ./release-upload

Draft instructions in release-cf.sh

### release utilities:

 - paraput.py: parallel s3 uploader
 - upload-index.py: uploades index.json with correct header and acl
 - upload.sh: a runner for pointing at an unzip export tarball

# TODO

 - Fully automate this so we can recreate the build box if necessary.
 - move to own vagrant file that automatically runs ansible provisioner
 - prefixing of index for architecture
 - package health checks

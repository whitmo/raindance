# Release workflow

Raindance's main function is to create a juju consumable package
collection. The cli provides basic helpers for this task, but to
actually create a release, we must do several external steps.

The current flow spins up an ec2 instance (specially prepared by
pivotal to run bosh-lite) and installs raindance upon it, then
harvests the resulting packages.

## Setup work instance

We'll need to launch bosh-lite into ec2.

 0. Create a var.sh::
    ```
    export AWS_ACCESS_KEY="AWS_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="AWS_SECRET_KEY"
    ```
    Source it::

    ```
    source ./var.sh
    ```

From this folder in the raindance repository:

 `./run-aws.sh {release version}`


## What it does

The runner drives an ansible playbook that does the following:

 - creates a security group
 - launches an 50G ec2 instance (this process requires a bit of space)
 - installs cf-release and bosh-lite
 - creates and uploads release and manifest
 - deploys cf to the instance, imediately deletes deployment
 - exports compiled packages from bosh and uploads them and the job
   specs to s3

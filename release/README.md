# Release workflow

Raindance's main function is to create juju consumable
"artifacts". The cli provides basic helpers for this task, but to
actually create a release, we must do several external steps.

The current flow spins up an ec2 instance and install boshlite upon
it, then harvests the resulting packages.

## Setup work instance

We'll need to launch bosh-lite into ec2.

 0. Create a var.sh and source: ala::
    ```
    export AWS_ACCESS_KEY="AWS_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="AWS_SECRET_KEY"
    ```

From this repository:

 `./run-aws.sh {release version}`

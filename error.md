TASK: [run export] ************************************************************

<54.174.47.185> REMOTE_MODULE async_status jid=11837425011.15937
failed: [54.174.47.185] =>

{
    "start": "2014-11-20 19:27:04.991713",
    "rc": 1,
    "finished": 1,
    "end": "2014-11-20 19:27:06.243801",
    "delta": "0:00:01.252088",
    "cmd": "source /home/ubuntu/.boilerplate-src.sh && bosh export compiled_packages cf/193 bosh-warden-boshlite-ubuntu-trusty-go_agent/3 /opt/packages",
    "changed": true,
    "ansible_job_id": "11837425011.15937"
}

stderr: The Bosh Lite Director bosh director doesn't understand the following API call: /compiled_package_groups/export. The bosh deployment may need to be upgraded.

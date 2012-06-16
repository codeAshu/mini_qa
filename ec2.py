#### ec2.py
#
# Creates a small instance at EC2, and sshes you into it.
#
#### Possible additions
#
# + Extend so it can be used with clusters, not just single machines
# + Make it so clusters (or machines) are named.
# + Consider integration with Puppet or Chef or Fabric

# Standard library
import os
import sys
import time

# Third party libraries
from boto.ec2.connection import EC2Connection

# The list of EC2 AMIs to use, from alestic.com
AMIS = {"m1.small" : "ami-e2af508b",
        "c1.medium" : "ami-e2af508b",
        "m1.large" : "ami-68ad5201",
        "m1.xlarge" : "ami-68ad5201",
        "m2.xlarge" : "ami-68ad5201",
        "m2.2xlarge" : "ami-68ad5201",
        "m2.4xlarge" : "ami-68ad5201",
        "c1.xlarge" : "ami-68ad5201",
        "cc1.4xlarge" : "ami-1cad5275"
        }

def stop():
    """
    Terminate the first running EC2 instance we can find.  Should be
    used with care: if you have multiple EC2 instances running it may
    terminate the wrong instance.
    """
    instance = get_running_instance()
    ec2_conn = EC2Connection(
        os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
    ec2_conn.terminate_instances([instance.id ])

def get_running_instance():
    """
    Return the first running EC2 instance that can be found.
    """
    ec2_conn = EC2Connection(
        os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
    reservations = ec2_conn.get_all_instances()
    running_instances = [instance for reservation in reservations
                         for instance in reservation.instances 
                         if instance.update() == u"running"]
    return running_instances[0]

def ssh_cmd():
    """
    Find a running EC2 instance and login.
    """
    login(get_running_instance())

def login(instance):
    """
    ssh to `instance`.
    """
    print "SSHing to instance with address %s" % (instance.public_dns_name)
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    os.system("ssh -i %s ubuntu@%s" % (keypair, instance.public_dns_name))

def start():
    """
    Create an EC2 instance, set it up, and login.
    """
    instance = create_ec2_instance("m1.small")
    setup(instance)
    login(instance)

def create_ec2_instance(instance_type):
    """
    Create an EC2 instance of type ``instance_type``. 
    """
    try:
        ami = AMIS[instance_type]
    except:
        ami = AMIS["m1.small"]
    ec2_conn = EC2Connection(
        os.environ["AWS_ACCESS_KEY_ID"], os.environ["AWS_SECRET_ACCESS_KEY"])
    image = ec2_conn.get_all_images(image_ids=[ami])[0]
    reservation = image.run(
        1, 1, os.environ["AWS_KEYPAIR"], instance_type=instance_type)
    instance = reservation.instances[0]
    # Wait for the instance to come up
    while instance.update()== u'pending':
        time.sleep(2)
    # Give the ssh daemon time to start
    time.sleep(120) 
    return instance

def setup(instance):
    """
    Copy `setup.sh` to `instance` and run it.
    """
    scp([instance], "setup.sh")
    ssh([instance], "bash setup.sh", False)

def scp(instances, local_filename, remote_filename=False):
    """
    scp ``local_filename`` to ``remote_filename`` on ``instances``.
    If ``remote_filename`` is not set or is set to ``False`` then
    ``remote_filename`` is set to ``local_filename``.
    """
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"], os.environ["AWS_KEYPAIR"])
    if not remote_filename:
        remote_filename = local_filename
    for instance in instances:
        os.system("scp -r -i %s %s ubuntu@%s:%s" % (
                keypair, local_filename, 
                instance.public_dns_name, remote_filename))

def ssh(instances, cmd, background=False):
    """
    Run ``cmd`` on the command line on ``instances``.  Runs in the
    background if ``background == True``.
    """
    keypair = "%s/%s.pem" % (os.environ["AWS_HOME"],
                             os.environ["AWS_KEYPAIR"])
    append = {True: " &", False: ""}[background]
    for instance in instances:
        remote_cmd = "'nohup %s > foo.out 2> foo.err < /dev/null %s'" % (
            cmd, append)
        os.system(
            "ssh -o BatchMode=yes -i %s ubuntu@%s %s" % (
                keypair, instance.public_dns_name, remote_cmd))

if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == "stop":
        stop()
    elif arg == "ssh":
        ssh_cmd()
    else: # start
        start()
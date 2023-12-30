from __future__ import print_function

from os import path

from fabric.contrib.files import exists
from offregister_fab_utils.apt import apt_depends
from offregister_fab_utils.git import clone_or_update
from offregister_fab_utils.ruby import install as install_ruby


def _step0(c, *args, **kwargs):
    _build_and_upload_deb(version="0.28.1")


def step0(c, *args, **kwargs):
    master = kwargs.pop("master", False)
    version = "0.28.1"
    if c.run(
        "dpkg-query --showformat='${Version}' --show mesos", warn=True
    ).stdout.startswith(version):
        c.local(
            "echo {command} {version} is already installed".format(
                command="mesos", version=version
            )
        )
        return "mesos already installed"

    apt_depends(c, "curl", "openjdk-7-jre-headless")  # 'gdebi',
    c.run("mkdir -p $HOME/downloads")

    with c.cd("$HOME/downloads"):
        package = "mesos-{version}-gcc4.8-amd64.deb".format(version=version)
        if not exists(c, runner=c.run, path=package):
            c.run(
                "curl -OL https://github.com/offscale/packages/raw/master/{package}".format(
                    package=package
                )
            )
        # c.sudo('gdebi --non-interactive {package}'.format(package=package))
        c.sudo("dpkg -i {package}".format(package=package), warn=True)
        c.sudo("apt-get --yes --fix-broken install")

    apt_depends(c, "python-pip")
    env = dict(HOME=c.run("echo $HOME").stdout.rstrip())
    c.sudo("python -m pip install mesos.cli mesos.interface", env=env)

    _install_conf(master, MASTER_IP="127.0.0.1")

    return "mesos installed"


def _install_conf(master, **template_vars):
    conf_name = "mesos-{}.conf".format("master" if master else "slave")
    upload_template_fmt(
        c,
        path.join(path.dirname(__file__), "data", conf_name),
        "/etc/init/{}".format(conf_name),
        context=template_vars,
        use_sudo=True,
    )


def _build_and_upload_deb(version):
    c.sudo("apt-get update -qq")
    c.sudo("apt-get upgrade -y")
    c.sudo("apt-get dist-upgrade -y")
    apt_depends(
        c,
        "openjdk-7-jdk",
        "build-essential",
        "python-dev",
        "python-boto",
        "curl",
        "libcurl4-nss-dev",
        "libsasl2-dev",
        "maven",
        "libapr1-dev",
        "libsvn-dev",
        "git",
        "autoconf",
    )

    install_ruby()

    from offregister_fab_utils import Package
    from offregister_fab_utils.apt import is_installed

    print("----------------------------------------------------------------------")
    print(
        "is_installed(Package('ruby', '2.3')) =", is_installed(Package("ruby", "2.3"))
    )
    apt_depends(c, "software-properties-common")
    c.sudo("apt-add-repository -y ppa:brightbox/ruby-ng")
    apt_depends(
        c,
        "ruby{version}".format(version="2.3"),
        "ruby{version}-dev".format(version="2.3"),
    )

    print("----------------------------------------------------------------------")
    clone_or_update(
        team="deric",
        repo="mesos-deb-packaging",
        branch="master",
        skip_checkout=True,
        skip_reset=True,
    )

    pkg = "mesos-{version}-gcc4.8-amd64.deb".format(version=version)
    with c.cd("mesos-deb-packaging"):
        c.run(
            "bash build_mesos --ref {version} --build-version p1".format(
                version=version
            )
        )
        c.run("mv pkg.deb {pkg}".format(pkg=pkg))
    clone_or_update(
        c,
        team="offscale",
        repo="packages",
        branch="master",
        skip_checkout=True,
        skip_reset=True,
    )
    with c.cd("packages"):
        c.run("git add {pkg}".format(pkg=pkg))
        c.run('git commit -am "Built {pkg}"'.format(pkg=pkg))
        c.run("git push -u origin master")


def step1(c, *args, **kwargs):
    c.run("service status mesos-master")
    c.run("service status mesos-slave")
    raise NotImplementedError()

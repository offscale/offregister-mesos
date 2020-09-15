from os import path

from fabric.api import run, sudo, local, shell_env
from fabric.contrib.files import exists, upload_template

from offregister_fab_utils.apt import apt_depends, cd
from offregister_fab_utils.git import clone_or_update
from offregister_fab_utils.ruby import install as install_ruby


def _step0(*args, **kwargs):
    _build_and_upload_deb(version="0.28.1")


def step0(*args, **kwargs):
    master = kwargs.pop("master", False)
    version = "0.28.1"
    if run(
        "dpkg-query --showformat='${Version}' --show mesos", warn_only=True
    ).startswith(version):
        local(
            "echo {command} {version} is already installed".format(
                command="mesos", version=version
            )
        )
        return "mesos already installed"

    apt_depends("curl", "openjdk-7-jre-headless")  # 'gdebi',
    run("mkdir -p $HOME/downloads")

    with cd("$HOME/downloads"):
        package = "mesos-{version}-gcc4.8-amd64.deb".format(version=version)
        if not exists(package):
            run(
                "curl -OL https://github.com/offscale/packages/raw/master/{package}".format(
                    package=package
                )
            )
        # sudo('gdebi --non-interactive {package}'.format(package=package))
        sudo("dpkg -i {package}".format(package=package), warn_only=True)
        sudo("apt-get --yes --fix-broken install")

    apt_depends("python-pip")
    with shell_env(HOME=run("echo $HOME")):
        sudo("pip install mesos.cli mesos.interface")

    _install_conf(master, MASTER_IP="127.0.0.1")

    return "mesos installed"


def _install_conf(master, **template_vars):
    conf_name = "mesos-{}.conf".format("master" if master else "slave")
    upload_template(
        path.join(path.dirname(__file__), "data", conf_name),
        "/etc/init/{}".format(conf_name),
        context=template_vars,
        use_sudo=True,
    )


def _build_and_upload_deb(version):
    sudo("apt-get update -qq")
    sudo("apt-get upgrade -y")
    sudo("apt-get dist-upgrade -y")
    apt_depends(
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

    from offregister_fab_utils.apt import is_installed, Package

    print("----------------------------------------------------------------------")
    print(
        ("is_installed(Package('ruby', '2.3')) =", is_installed(Package("ruby", "2.3")))
    )
    apt_depends("software-properties-common")
    sudo("apt-add-repository -y ppa:brightbox/ruby-ng")
    apt_depends(
        "ruby{version}".format(version="2.3"), "ruby{version}-dev".format(version="2.3")
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
    with cd("mesos-deb-packaging"):
        run(
            "bash build_mesos --ref {version} --build-version p1".format(
                version=version
            )
        )
        run("mv pkg.deb {pkg}".format(pkg=pkg))
    clone_or_update(
        team="offscale",
        repo="packages",
        branch="master",
        skip_checkout=True,
        skip_reset=True,
    )
    with cd("packages"):
        run("git add {pkg}".format(pkg=pkg))
        run('git commit -am "Built {pkg}"'.format(pkg=pkg))
        run("git push -u origin master")


def step1(*args, **kwargs):
    run("service status mesos-master")
    run("service status mesos-slave")
    raise NotImplementedError()

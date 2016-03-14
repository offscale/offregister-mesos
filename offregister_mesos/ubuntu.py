from os import path

from fabric.api import run, sudo, local, shell_env
from fabric.contrib.files import exists, upload_template

from offregister_fab_utils.apt import apt_depends, cd
from offregister_fab_utils.git import clone_or_update
from offregister_fab_utils.ruby import install as install_ruby


def install(*args, **kwargs):
    master = kwargs.pop('master', False)
    version = '0.27.0'
    if run("dpkg-query --showformat='${Version}' --show mesos", warn_only=True).startswith(version):
        local('echo {command} {version} is already installed'.format(command='mesos', version=version))
        return 'mesos already installed'

    apt_depends('curl',  # 'gdebi',
                'openjdk-7-jre-headless')
    run('mkdir -p $HOME/downloads')

    with cd('$HOME/downloads'):
        package = 'mesos-0.27.0-gcc4.8-amd64.deb'
        if not exists(package):
            run('curl -OL https://github.com/offscale/packages/raw/master/{package}'.format(package=package))
        # sudo('gdebi --non-interactive {package}'.format(package=package))
        sudo('dpkg -i {package}'.format(package=package), warn_only=True)
        sudo('apt-get --yes --fix-broken install')

    apt_depends('python-pip')
    with shell_env(HOME=run('echo $HOME')):
        sudo('pip install mesos.cli mesos.interface')

    install_conf(master, MASTER_IP='127.0.0.1')

    return 'mesos installed'


def install_conf(master, **template_vars):
    conf_name = 'mesos-{}.conf'.format('master' if master else 'slave')
    upload_template(
        path.join(path.dirname(__file__), 'data', conf_name),
        '/etc/init/{}'.format(conf_name), context=template_vars, use_sudo=True
    )


def build_and_upload_deb(version):
    apt_depends('openjdk-7-jdk', 'build-essential', 'python-dev', 'python-boto', 'curl',
                'libcurl4-nss-dev', 'libsasl2-dev', 'maven', 'libapr1-dev', 'libsvn-dev',
                'git', 'autoconf')

    install_ruby()
    clone_or_update(team='deric', repo='mesos-deb-packaging',
                    branch='master', skip_checkout=True, skip_reset=True)
    with cd('mesos-deb-packaging'):
        pkg = 'mesos-{version}-gcc4.8-amd64.deb'.format(version=version)
        run('bash build_mesos --ref {version} --build-version p1'.format(version=version))
        run('mv pkg.deb {pkg}'.format(pkg=pkg))
    run('git clone https://github.com/offscale/packages')
    with cd('packages'):
        run('git add {pkg}'.format(pkg=pkg))
        run('git commit -am "Built {pkg}"'.format(pkg=pkg))
        run('git push -u origin master')


def serve(*args, **kwargs):
    run('service status mesos-master')
    run('service status mesos-slave')
    raise NotImplementedError()

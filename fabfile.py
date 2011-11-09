from fabric.api import env, local, sudo, put, settings, run, cd
from fabric.contrib.files import append
import os

env.user = 'ahjohannessen'
env.hosts = ['172.16.122.135']

env.mono_src = 'git/mono'
env.mono_branch = 'mono-2-10'
env.mono_location = '/opt/%s' % env.mono_branch

env.agent_zip = 'buildAgent.zip'
env.agent_link = 'http://teamcity.codebetter.com/update/%s' % env.agent_zip
env.agent_server_url = 'http://tc'
env.agent_location = '/opt/buildagent'

def install():
    apt_latest()
    install_git()

    fetch_mono_src()

    install_mono_distro()
    install_mono_compile_deps()

    compile_mono()

    install_jre()
    install_ruby_and_gems()

    install_zip()
    install_upstart()
    install_buildagent()

# Mono

def fetch_mono_src():
    with settings(warn_only=True):
        if run("test -d %s" % env.mono_src).failed:
            run("git clone git://github.com/mono/mono.git %s" % env.mono_src)
    with cd(env.mono_src):
        run('git checkout %s' % env.mono_branch)
        run('git reset --hard HEAD && git clean -xfd && git pull')

def install_mono_distro():
    sudo('apt-get install -y mono-complete', pty=True)

def install_mono_compile_deps():
    sudo('apt-get install -y build-essential automake autoconf gettext libtool intltool gawk bison flex', pty=True)

def compile_mono():
    with cd(env.mono_src):
        run('./autogen.sh --prefix=%(mono_location)s' % env)
        run('make')
        sudo('make install', pty=True)

# Misc Dependencies


def apt_latest():
    sudo('apt-get update && apt-get upgrade -y', pty=True)

def install_git():
    sudo('apt-get install -y git-core', pty=True)


def install_jre():
    sudo('apt-get install -y openjdk-7-jre-headless')

def install_ruby_and_gems():
    sudo('apt-get install -y ruby') 
    sudo('apt-get install -y rubygems')

    sudo('gem install rake --no-rdoc --no-ri')
    sudo('gem install rubyzip --no-rdoc --no-ri')
    sudo('gem install albacore --no-rdoc --no-ri')

def install_upstart():
    sudo('apt-get install -y upstart')

def install_zip():
    sudo('apt-get install -y unzip', pty=True)

# Build Agent

def fetch_buildagent(agent_dir):
    with cd('~'):
        run('wget --no-verbose %s' % env.agent_link, pty=True)
        run('unzip %s -d %s' % (env.agent_zip, agent_dir), pty=True)
        run('rm %s' % env.agent_zip, pty=True)


def install_buildagent():
    agent_dir = 'buildagent'
    fetch_buildagent(agent_dir)

    with cd(agent_dir):
        run('chmod +x bin/agent.sh', pty=True)

        with cd('conf'):
            run('cp buildAgent.dist.properties buildAgent.properties', pty=True)
            if env.agent_server_url:
                replace_agent_property('serverUrl', env.agent_server_url, 'buildAgent.properties')

            append_agent_property('env.PATH', env.mono_location + ':%env.PATH%', 'buildAgent.properties')

    sudo('cp -R %s/* %s' % (agent_dir, env.agent_location), pty=True)
    
    install_buildagent_upstarts()

def install_buildagent_upstarts():

    start = 'start-tca.conf'
    stop = 'stop-tca.conf'

    local('cat tmpl-start-tca.conf | sed -e "s:AGENT_LOC:%s:g" > %s' % (env.agent_location, start))
    local('cat tmpl-stop-tca.conf | sed -e "s:AGENT_LOC:%s:g" > %s' % (env.agent_location, stop))

    put(start, '/etc/init/%s' % start, use_sudo=True)
    put(stop, '/etc/init/%s' % stop, use_sudo=True)

    local('rm %s && rm %s' % (start, stop))

def append_agent_property(name, value, propfile):
    append(propfile, '%s%s=%s' % (os.linesep, name, value))

def replace_agent_property(name, value, propfile):
    run("sed '/%s=/ c\%s%s=%s' %s" % (name, os.linesep, name, value, propfile))

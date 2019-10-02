#!/usr/bin/env python3
import click
from urllib.request import urlopen
from importlib import util
import sys
import shutil
import time
import inspect
import argparse
import os

DEFAULT_BRANCH = "development"
os.environ["LC_ALL"] = "en_US.UTF-8"


def load_install_tools(branch=None):
    # get current install.py directory
    path = "/sandbox/code/github/threefoldtech/jumpscaleX_core/install/InstallTools.py"
    if not branch:
        branch = DEFAULT_BRANCH
    # first check on code tools
    if not os.path.exists(path):
        rootdir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(rootdir, "InstallTools.py")
        # now check on path next to jsx
        if not os.path.exists(path) or path.find("/code/") == -1:
            url = "https://raw.githubusercontent.com/threefoldtech/jumpscaleX_core/%s/install/InstallTools.py" % branch

            with urlopen(url) as resp:
                if resp.status != 200:
                    raise RuntimeError("fail to download InstallTools.py")
                with open(path, "w+") as f:
                    f.write(resp.read().decode("utf-8"))
                print("DOWNLOADED INSTALLTOOLS TO %s" % path)

    spec = util.spec_from_file_location("IT", path)
    IT = spec.loader.load_module()
    IT.MyEnv.init()
    # if path.find("/code/") != -1:  # means we are getting the installtools from code dir
    #     check_branch(IT)
    return IT


# def check_branch(IT):
#     HOMEDIR = os.environ["HOME"]
#     paths = ["/sandbox/code/github/threefoldtech/jumpscaleX", "%s/code/github/threefoldtech/jumpscaleX" % HOMEDIR]
#     for path in paths:
#         if os.path.exists(path):
#             cmd = "cd %s; git branch | grep \* | cut -d ' ' -f2" % path
#             rc, out, err = IT.Tools.execute(cmd)
#             if out.strip() != DEFAULT_BRANCH:
#                 print("WARNING the branch of jumpscale in %s needs to be %s" % (path, DEFAULT_BRANCH))
#                 if not IT.Tools.ask_yes_no("OK to work with branch above?"):
#                     sys.exit(1)


IT = load_install_tools()
IT.MyEnv.interactive = True  # std is interactive

# get Docker factory inited
DF = IT.DockerFactory
DF.init()


def jumpscale_get(die=True):
    # jumpscale need to be available otherwise cannot do
    try:
        from Jumpscale import j
    except Exception as e:
        if die:
            raise RuntimeError("ERROR: cannot use jumpscale yet, has not been installed")
        return None
    return j


# have to do like this, did not manage to call the click enabled function (don't know why)
def _configure(
    basedir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey_words=None,
    secret=None,
    configdir=None,
):
    interactive = not no_interactive
    sshagent_use = not no_sshagent

    IT.MyEnv.configure(
        basedir=basedir,
        readonly=None,
        codedir=codedir,
        sshkey=sshkey,
        sshagent_use=sshagent_use,
        debug_configure=debug,
        interactive=interactive,
        secret=secret,
        configdir=configdir,
    )
    j = jumpscale_get(die=False)

    if not j and privatekey_words:
        raise RuntimeError(
            "cannot load jumpscale, \
            can only configure private key when jumpscale is installed locally use jsx install..."
        )

    if j and privatekey_words:
        j.data.nacl.configure(privkey_words=privatekey_words)


"""
if not IT.MyEnv.state:
    # this is needed to make sure we can install when nothing has been done yet
    _configure()

# IT.BaseInstaller.base()
"""


@click.group()
def cli():
    pass


# CONFIGURATION (INIT) OF JUMPSCALE ENVIRONMENT
@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if /sandbox exists otherwise ~/sandbox")
@click.option("--codedir", default=None, help="path where the github code will be checked out, default sandbox/code")
@click.option(
    "--basedir",
    default=None,
    help="path where JSX will be installed default /sandbox if /sandbox exists otherwise ~/sandbox",
)
@click.option("--no-sshagent", is_flag=True, help="do you want to use an ssh-agent")
@click.option("--sshkey", default=None, help="if more than 1 ssh-key in ssh-agent, specify here")
@click.option("--debug", is_flag=True, help="do you want to put kosmos in debug mode?")
@click.option("-s", "--no-interactive", is_flag=True, help="default is interactive")
@click.option(
    "--privatekey",
    default=False,
    help="24 words, use '' around the private key if secret specified and private_key not then will ask in -y mode will autogenerate",
)
@click.option(
    "--secret", default=None, help="secret for the private key (to keep secret), default will get from ssh-key"
)
def configure(
    basedir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey=None,
    secret=None,
    configdir=None,
):
    """
    initialize 3bot (JSX) environment
    """

    return _configure(
        basedir=basedir,
        codedir=codedir,
        debug=debug,
        sshkey=sshkey,
        no_sshagent=no_sshagent,
        no_interactive=no_interactive,
        privatekey_words=privatekey,
        secret=secret,
    )


# INSTALL OF JUMPSCALE IN CONTAINER ENVIRONMENT
@click.command(name="container-install")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option(
    "--scratch", is_flag=True, help="from scratch, means will start from empty ubuntu and re-install everything"
)
@click.option("-d", "--delete", is_flag=True, help="if set will delete the docker container if it already exists")
@click.option("--threebot", is_flag=True, help="also install the threebot")
@click.option(
    "-i",
    "--image",
    default=None,
    help="select the container image to use to create the container, leave empty unless you know what you do (-:",
)
@click.option(
    "-b", "--branch", default=None, help="jumpscale branch. default 'master' or 'development' for unstable release"
)
@click.option(
    "--pull",
    is_flag=True,
    help="pull code from git, if not specified will only pull if code directory does not exist yet",
)
@click.option(
    "-r",
    "--reinstall",
    is_flag=True,
    help="reinstall, basically means will try to re-do everything without removing the data",
)
@click.option("--develop", is_flag=True, help="will use the development docker image to start from.")
@click.option("-s", "--no-interactive", is_flag=True, help="default is interactive, -s = silent")
def container_install(
    name="3bot",
    scratch=False,
    delete=True,
    threebot=False,
    image=None,
    branch=None,
    reinstall=False,
    no_interactive=False,
    pull=False,
    configdir=None,
    develop=False,
):
    """
    create the 3bot container and install jumpcale inside
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments

    if you want to configure other arguments use 'jsx configure ... '

    """

    IT = load_install_tools(branch=branch)
    # IT.MyEnv.interactive = True
    # interactive = not no_interactive

    _configure(configdir=configdir, no_interactive=no_interactive)

    if scratch:
        image = "threefoldtech/base"
        if scratch:
            delete = True
        reinstall = True
    if not image:
        if not develop:
            image = "threefoldtech/3bot"
        else:
            image = "threefoldtech/3botdevel"

    if not branch:
        branch = IT.DEFAULT_BRANCH

    docker = IT.DockerContainer(name=name, delete=delete, image=image)

    docker.install()

    # if prebuilt:
    #     docker.sandbox_sync()

    installer = IT.JumpscaleInstaller()
    installer.repos_get(pull=False)

    docker.jumpscale_install(branch=branch, redo=reinstall, pull=pull, threebot=threebot)  # , prebuilt=prebuilt)


def container_get(name="3bot", delete=False, jumpscale=False):
    IT.MyEnv.sshagent.key_default_name
    docker = DF.container_get(name=name, image="threefoldtech/3bot", start=True, delete=delete)
    if jumpscale:
        # needs to stay because will make sure that the config is done properly in relation to your shared folders from the host
        docker.jumpscale_install()
    return docker


# INSTALL OF JUMPSCALE IN CONTAINER ENVIRONMENT
@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("--threebot", is_flag=True, help="also install the threebot system")
# @click.option("--no-sshagent", is_flag=True, help="do you want to use an ssh-agent")
@click.option("--prebuilt", is_flag=True, help="if set will allow a quick start using prebuilt threebot")
@click.option(
    "-b", "--branch", default=None, help="jumpscale branch. default 'master' or 'development' for unstable release"
)
@click.option(
    "--pull",
    is_flag=True,
    help="pull code from git, if not specified will only pull if code directory does not exist yet",
)
@click.option(
    "-r",
    "--reinstall",
    is_flag=True,
    help="reinstall, basically means will try to re-do everything without removing the data",
)
@click.option("-s", "--no-interactive", is_flag=True, help="default is interactive, -s = silent")
def install(threebot=False, branch=None, reinstall=False, pull=False, no_interactive=False, prebuilt=False):
    """
    install jumpscale in the local system (only supported for Ubuntu 18.04+ and mac OSX, use container install method otherwise.
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments

    if you want to configure other arguments use 'jsx configure ... '

    """
    # print("DEBUG:: no_sshagent", no_sshagent, "configdir", configdir)  #no_sshagent=no_sshagent
    IT = load_install_tools(branch=branch)
    # IT.MyEnv.interactive = True
    _configure(configdir="/sandbox/cfg", basedir="/sandbox", no_interactive=no_interactive)
    SANDBOX = IT.MyEnv.config["DIR_BASE"]
    if reinstall:
        # remove the state
        IT.MyEnv.state_reset()
        force = True
    else:
        force = False

    if not branch:
        branch = IT.DEFAULT_BRANCH

    installer = IT.JumpscaleInstaller()
    installer.install(sandboxed=False, force=force, gitpull=pull, prebuilt=prebuilt)
    if threebot:
        IT.Tools.execute(
            "source %s/env.sh;kosmos 'j.servers.threebot.install()'" % SANDBOX, showout=True, timeout=3600 * 2
        )
        # IT.Tools.execute("source %s/env.sh;kosmos 'j.servers.threebot.test()'" % SANDBOX, showout=True)

    # LETS NOT DO THE FOLLOWING TAKES TOO LONG
    # IT.Tools.execute("source %s/env.sh;kosmos 'j.core.tools.system_cleanup()'" % SANDBOX, showout=True)
    print("Jumpscale X installed successfully")


@click.command(name="container-import")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/saendbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-i", "--imagename", default="threefoldtech/3bot", help="name of image where we will import to")
@click.option("-p", "--path", default=None, help="image location")
@click.option("--no-start", is_flag=True, help="container will start auto")
def container_import(name="3bot", path=None, imagename="threefoldtech/3bot", no_start=False, configdir=None):
    """
    import container from image file, if not specified will be /tmp/3bot.tar
    :param args:
    :return:
    """
    start = not no_start
    docker = container_get(delete=True, name=name)
    docker.import_(path=path, imagename=imagename, start=start)


@click.command(name="container-export")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-p", "--path", default=None, help="image location")
@click.option("-v", "--version", default=None, help="image location")
def container_export(name="3bot", path=None, version=None, configdir=None):
    """
    export the 3bot to image file, if not specified will be /tmp/3bot.tar
    :param name:
    :param path:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name)
    docker.export(path=path, version=version)


@click.command(name="container-save")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option(
    "--dest", default="threefoldtech/3bot", help="name of container image on docker hub, default threefoldtech/3bot"
)
@click.option("-p", "--push", is_flag=True, help="push to docker hub")
@click.option("-c", "--clean", is_flag=True, help="clean runtime")
@click.option("-cd", "--cleandevel", is_flag=True, help="clean development env")
def container_save(name="3bot", dest=None, push=False, clean=False, cleandevel=False, configdir=None):
    """
    starts from an export, if not there will do the export first
    :param name:
    :param path:
    :return:
    """
    if not dest:
        dest = "threefoldtech/3bot"
    _configure(configdir=configdir)
    docker = container_get(name=name)
    docker.save(image=dest, clean_runtime=clean, clean_devel=cleandevel)
    if push:
        docker.push()


@click.command(name="container-stop")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_stop(name="3bot", configdir=None):
    """
    stop the 3bot container
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    if name in DF.containers_running():
        docker = container_get(name=name)
        docker.stop()


@click.command(name="basebuilder")
@click.option(
    "--dest", default="threefoldtech/base", help="name of container image on docker hub, default threefoldtech/3bot"
)
@click.option("-p", "--push", is_flag=True, help="push to docker hub")
@click.option("-c", "--cont", is_flag=True, help="don't delete continue a previously stopped run")
def basebuilder(dest=None, push=False, configdir=None, cont=False):
    """
    create the base ubuntu docker which we can use as base for everything
    :param dest: default threefoldtech/base  the base is the base ubuntu image
    :return:
    """
    delete = not cont
    basebuilder_(dest=dest, push=push, configdir=configdir, delete=delete)


def basebuilder_(dest=None, push=False, configdir=None, delete=True):
    if not dest:
        dest = "threefoldtech/base"
    IT = load_install_tools(branch=DEFAULT_BRANCH)
    _configure(configdir=configdir)

    image = "phusion/baseimage:master"
    # image = "unilynx/phusion-baseimage-1804"
    docker = IT.DockerContainer(name="base", delete=delete, image=image)
    docker.install(update=True, stop=delete)
    docker.save(image=dest, clean_runtime=True)
    if push:
        docker.push()
    if delete:
        docker.stop()
    print("- *OK* base has been built, as image & exported")


@click.command(name="threebotbuilder")
@click.option("-p", "--push", is_flag=True, help="push to docker hub")
@click.option("-b", "--base", is_flag=True, help="build base image as well")
@click.option("-c", "--cont", is_flag=True, help="don't delete continue a previously stopped run")
def threebotbuilder(push=False, configdir=None, base=False, cont=False):
    """
    create the base for a 3bot
    if 3bot then will also create a 3botdevel which is with the development tools inside
    :param dest: default threefoldtech/base  the base is the base ubuntu image
    :return:
    """
    delete = not cont
    if base:
        basebuilder_(push=push, configdir=configdir)
    dest = "threefoldtech/3bot"

    IT = load_install_tools(branch=DEFAULT_BRANCH)
    _configure(configdir=configdir)

    docker = IT.DockerContainer(name="3botdev", delete=delete, image="threefoldtech/base")

    docker.install(update=delete, stop=delete)

    installer = IT.JumpscaleInstaller()
    installer.repos_get(pull=False)

    docker.jumpscale_install(branch=DEFAULT_BRANCH, redo=delete, pull=False, threebot=True)

    docker.save(clean_runtime=True, image=dest + "dev")
    from pudb import set_trace

    set_trace()
    if push:
        docker.push()

    docker = IT.DockerContainer(name="3bot", delete=True, image=dest + "dev")
    docker.install(update=False)
    from pudb import set_trace

    set_trace()
    docker.save(image=dest, clean_devel=True)
    if push:
        docker.push()

    docker.image = dest

    print("- *OK* threebot container has been built, as image & exported")


@click.command(name="container-start")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_start(name="3bot", configdir=None):
    """
    start the 3bot container
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name)
    docker.start()


@click.command(name="container-delete")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-a", "--all", is_flag=True, help="delete all")
def container_delete(name="3bot", all=None, configdir=None):
    """
    delete the 3bot container
    :param name:
@click.option("-n", "--name", default="3bot", help="name of container")
    :return:
    """
    _configure(configdir=configdir)
    if all:
        for name in DF.containers_names():
            docker = container_get(name=name)
            docker.delete()
    else:
        if not DF.container_name_exists(name):
            return None
        docker = container_get(name=name)
        docker.delete()


@click.command(name="container-reset")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
def containers_reset(configdir=None):
    """
    remove all docker containers & images
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    DF.reset()


@click.command(name="containers")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
def containers(configdir=None):
    """
    remove all docker containers & imagess
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    DF.list()


@click.command(name="container-kosmos")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_kosmos(name="3bot", configdir=None):
    """
    open a kosmos shell in container
    :param name: name of container if not the default =  3bot
    :return:
    """
    docker = container_get(name=name)
    os.execv(
        shutil.which("ssh"),
        [
            "ssh",
            "root@localhost",
            "-A",
            "-t",
            "-oStrictHostKeyChecking=no",
            "-p",
            str(docker.config.sshport),
            "source /sandbox/env.sh;kosmos",
        ],
    )


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-t", "--target", default="auto", help="auto,local,container, default is auto will try container first")
def kosmos(name="3bot", target="auto", configdir=None):
    j = jumpscale_get(die=True)
    j.application.interactive = True
    n = j.data.nacl.get(load=False)  # important to make sure private key is loaded
    if n.load(die=False) is False:
        n.configure()
    j.application.bcdb_system  # needed to make sure we have bcdb running, needed for code completion
    j.shell(loc=False, locals_=locals(), globals_=globals())


@click.command(name="container-shell")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_shell(name="3bot", configdir=None):
    """
    open a  shell to the container for 3bot
    :param name: name of container if not the default
    :return:
    """
    docker = container_get(name=name)
    docker.sshshell()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def wireguard(name=None, configdir=None):
    """
    jsx wireguard
    enable wireguard, can be on host or server
    :return:
    """
    assert name
    if not DF.indocker():
        docker = container_get(name=name)
        # remotely execute wireguard
        docker.sshexec("source /sandbox/env.sh;jsx wireguard")
        docker.wireguard.connect()
    else:
        wg = IT.WireGuard()
        wg.server_start()


@click.command(name="modules-install")
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("--url", default="3bot", help="git url e.g. https://github.com/myfreeflow/kosmos")
def modules_install(url=None, configdir=None):
    """
    install jumpscale module in local system
    :return:
    """
    from Jumpscale import j

    path = j.clients.git.getContentPathFromURLorPath(url)
    _generate(path=path)


# @click.command()
# # @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
# # @click.option("-n", "--name", default="3bot", help="name of container")
# def bcdb_indexrebuild(configdir=None):
#     """
#     rebuilds the index for all BCDB or a chosen one (with name),
#     use this to fix corruption issues with index
#     if name is not given then will walk over all known BCDB's and rebuild index
#     :return:
#     """
#     from Jumpscale import j
#
#     j.data.bcdb.index_rebuild()


@click.command()
def generate():
    _generate()


@click.command()
def check():
    from Jumpscale import j

    j.application.interactive = True
    j.application.check()


def _generate(path=None):
    j = jumpscale_get(die=True)
    j.application.generate(path)


if __name__ == "__main__":

    cli.add_command(configure)
    cli.add_command(check)
    cli.add_command(install)
    cli.add_command(kosmos)
    cli.add_command(generate)
    cli.add_command(wireguard)
    cli.add_command(modules_install, "modules-install")

    # DO NOT DO THIS IN ANY OTHER WAY !!!
    if not DF.indocker():
        cli.add_command(container_kosmos, "container-kosmos")
        cli.add_command(container_install, "container-install")
        cli.add_command(container_stop, "container-stop")
        cli.add_command(container_start, "container-start")
        cli.add_command(container_delete, "container-delete")
        cli.add_command(containers_reset, "containers-reset")
        cli.add_command(container_export, "container-export")
        cli.add_command(container_import, "container-import")
        cli.add_command(container_shell, "container-shell")
        cli.add_command(container_save, "container-save")
        cli.add_command(basebuilder, "basebuilder")
        cli.add_command(threebotbuilder, "threebotbuilder")
        cli.add_command(containers, "containers")

    cli()

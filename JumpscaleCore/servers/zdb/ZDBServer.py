from Jumpscale import j

import socket


class ZDBServer(j.baseclasses.object_config):
    _SCHEMATEXT = """
           @url =  jumpscale.zdb.server.1
           name** = "default" (S)
           addr = "127.0.0.1" (S)
           port = 9900 (I)
           adminsecret_ = "" (S)
           executor = "tmux"
           mode = "seq"
           """

    def _init(self, **kwargs):
        self._datadir = ""
        if self.adminsecret_ == "":
            self.adminsecret_ = j.core.myenv.adminsecret
        assert len(self.adminsecret_) > 5

    @property
    def datadir(self):
        if not self._datadir:
            self._datadir = "%s/zdb-data/%s" % (j.core.myenv.config["DIR_VAR"], self.name)

        return self._datadir

    def isrunning(self):
        idir = "%s/zdb-index/" % (self.datadir)
        ddir = "%s/zdb-data/" % (self.datadir)
        if not j.sal.fs.exists(idir):
            return False
        if not j.sal.fs.exists(ddir):
            return False
        if not j.sal.nettools.tcpPortConnectionTest(self.addr, self.port):
            return False

        cl = self.client_admin_get()
        return cl.ping()

    def start(self):
        """
        start zdb in tmux using this directory (use prefab)
        will only start when the server is not life yet

        kosmos 'j.servers.zdb.default.start()'

        """
        self.startupcmd.start()
        self.client_admin_get()  # should also do a test, so we know if we can't connect

    def stop(self):
        self._log_info("stop zdb")
        self.startupcmd.stop()

    @property
    def startupcmd(self):

        # zdb doesn't understand hostname
        addr = socket.gethostbyname(self.addr)

        cmd = "zdb --listen %s --port %s --mode %s --admin %s --protect" % (
            self.addr,
            self.port,
            self.mode,
            self.adminsecret_,
        )

        return j.servers.startupcmd.get(
            name="zdb", cmd_start=cmd, path=self.datadir, ports=[self.port], executor=self.executor
        )

    def destroy(self):
        self.stop()
        self._log_info("destroy zdb")
        j.sal.fs.remove(self.datadir)
        # ipath = self.datadir+ "bcdbindex.db" % self.name

    @property
    def datadir(self):
        return j.core.tools.text_replace("{DIR_BASE}/var/zdb/%s/") % self.name

    def client_admin_get(self):
        """

        """
        cl = j.clients.zdb.client_admin_get(
            name=f"{self.name}_admin", addr=self.addr, port=self.port, secret=self.adminsecret_, mode=self.mode
        )
        assert cl.ping()
        return cl

    def client_get(self, name=None, nsname="default", secret="1234"):
        """
        get client to zdb

        """
        if not name:
            name = f"{self.name}"
        cl = j.clients.zdb.client_get(
            name=name, namespace=nsname, addr=self.addr, port=self.port, secret=secret, mode=self.mode
        )

        assert cl.ping()

        return cl

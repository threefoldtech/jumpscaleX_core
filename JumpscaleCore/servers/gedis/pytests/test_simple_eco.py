import os
import time
from multiprocessing import Process

import gevent
import pytest
from Jumpscale import j
import redis

from .actors.actor import SCHEMA_IN, SCHEMA_OUT


class TestSimpleEcho:
    @classmethod
    def setUpClass(cls):
        cls.server = j.servers.gedis.get(name="test", port=8889, host="0.0.0.0", ssl=False)
        actor_path = os.path.join(os.path.dirname(__file__), "actors/actor.py")
        cls.server.actor_add(actor_path)
        cls.server.save()
        cls.server.start()
        wait_start_server("127.0.0.1", 8889)
        cls.client = cls.server.client_get()
        cls.client.reload()
        time.sleep(3)
    
    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server.delete()

    def test_ping(self):
        assert b"PONG" == self.client.actors.actor.ping()
        assert b"test" == self.client.actors.actor.echo("test")
        time.sleep(2)

    def test_schema_in(self):
        x = j.data.schema.get_from_url(url="gedis.test.in").new()
        x.foo = "test"
        assert b"test" == self.client.actors.actor.schema_in(x)

    def test_schema_out(self):
        result = self.client.actors.actor.schema_out()
        assert result.bar == "test"

    def test_schema_in_out(self):
        x = j.data.schema.get_from_url(url="gedis.test.in").new()
        x.foo = "test"
        result = self.client.actors.actor.schema_in_out(x)
        assert result.bar == x.foo

    def test_schema_in_list_out(self):
        x = j.data.schema.get_from_url(url="gedis.test.in").new()
        x.foo = "test"
        result = self.client.actors.actor.schema_in_list_out(x)
        assert isinstance(result, list)
        # assert result.bar == x.foo

    def test_args_in(self):
        with pytest.raises((ValueError, TypeError)):
            self.client.actors.actor.args_in(12, "hello")

        with pytest.raises((ValueError, TypeError)):
            self.client.actors.actor.args_in({"foo"}, "hello")

        assert b"hello 1" == self.client.actors.actor.args_in("hello", 1)

    def test_error(self):
        with pytest.raises(j.exceptions.RemoteException):
            self.client.actors.actor.raise_error()
        # ensure the connection is still valid after an exception
        assert b"PONG" == self.client.actors.actor.ping()


def wait_start_server(addr, port):
    j.tools.timer.execute_until(
        lambda: j.sal.nettools.tcpPortConnectionTest(addr, port, timeout=10), timeout=10, interval=0.2
    )

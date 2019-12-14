from Jumpscale import j


class BCDBClient(j.baseclasses.object):
    def _init(self, **kwargs):
        self.name = kwargs["name"]
        self.bcdb = j.data.bcdb.get(name=self.name)
        self.model = self.bcdb.model_get(url=kwargs["url"])
        self.schema = self.model.schema
        self._rediscl_ = j.clients.redis.get(port=6380)

        self.iterate = self.model.iterate
        self.search = self.model.search
        self.find = self.model.find
        self.new = self.model.new
        self.exists = self.model.exists
        self.find_ids = self.model.find_ids
        self.get_by_name = self.model.get_by_name

        if self.bcdb.readonly:
            self.model.trigger_add(self._set_trigger)

    def get(self, id=None):
        if self.bcdb.readonly:
            key = f"{self.name}:data:1:{self.model.schema.url}"
            data = self._rediscl_.hget(key, str(id))
            ddata = j.data.serializers.json.loads(data)
            return self.model.new(ddata)
        else:
            return self.model.get(id=id)

    def set(self, obj):
        if self.bcdb.readonly:
            key = f"{self.name}:data:1:{obj._schema.url}"
            if obj.id:
                self._rediscl_.hset(key, str(obj.id), obj._json)
            else:
                r = self._rediscl_.execute_command("hsetnew", obj._json)
                j.shell()
        else:
            return self.model.set(obj=obj)

    def _set_trigger(self, obj, action="set_pre", propertyname=None, **kwargs):
        if action == "set_pre":
            self.set(obj)
            # call through redis client the local BCDB
            # get data as json (from _data) and use redis client to set to server
            return obj, True
        return obj, False


class BCDBClientFactory(j.baseclasses.object):

    __jslocation__ = "j.clients.bcdb"

    def _init(self, **kwargs):
        self._clients = j.baseclasses.dict()

    def get(self, url=None, schema=None, name=None):
        """
        :param name
        :return:
        """
        if schema:
            assert not url
            schema = j.data.schema.get_from_text(schema)
            url = schema.url
        if not name:
            name = "system"
        if name not in self._clients:
            self._clients[name] = BCDBClient(name=name, url=url)
        return self._clients[name]

    def test(self):
        """
        kosmos -p 'j.clients.bcdb.test()'
        :return:
        """

        # j.servers.threebot.local_start_default(background=True)

        b = j.clients.bcdb.get(url="jumpscale.sshclient.1")

        # print(b.find())

        obj = b.find()[0]

        obj = b.get(id=obj.id)
        obj.addr = "localhost"

        obj.save()

        obj2 = b.get(id=obj.id)
        assert obj2.addr == obj.addr

        print("TEST OK")
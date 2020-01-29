from Jumpscale import j


JSConfigs = j.baseclasses.object_config_collection


class LocationsConfiguration(j.baseclasses.object_config):
    """
    Website hosted in openresty
    This is port / hostname combination

    it will include locations from

    {DIR_BASE}/cfg/

    """

    _SCHEMATEXT = """
        @url = jumpscale.openresty.location
        name** = (S)
        path = "/sandbox/var/web/default" (S)
        locations_static = (LO) !jumpscale.openresty.location_static
        locations_proxy = (LO) !jumpscale.openresty.location_proxy
        locations_lapis = (LO) !jumpscale.openresty.location_lapis
        locations_custom = (LO) !jumpscale.openresty.location_custom
        locations_spa = (LO) !jumpscale.openresty.location_static
        mother_id** = 0 (I)

        @url = jumpscale.openresty.location_static
        name = "" (S)
        path_url = "/"
        path_location = ""
        index = "index.html"
        use_jumpscale_weblibs = false (B)

        @url = jumpscale.openresty.location_proxy
        name = "" (S)
        path_url = ""
        ipaddr_dest = (S)
        port_dest = (I)
        path_dest = "" (S)
        type = "http,websocket" (E)
        scheme = "http,https,ws,wss" (E)

        @url = jumpscale.openresty.location_lapis
        name = ""
        path_url = ""
        path_location = ""

        @url = jumpscale.openresty.location_custom
        name = ""
        config = ""

        """

    def get_location_proxy(self, new_location_name):
        return self.check_location_exists(self.locations_proxy, new_location_name)

    def get_location_static(self, new_location_name):
        return self.check_location_exists(self.locations_static, new_location_name)

    def get_locations_lapis(self, new_location_name):
        return self.check_location_exists(self.locations_lapis, new_location_name)

    def get_locations_spa(self, new_location_name):
        return self.check_location_exists(self.locations_spa, new_location_name)

    def get_locations_custom(self, new_location_name):
        return self.check_location_exists(self.get_locations_custom, new_location_name)

    @property
    def path_cfg_dir(self):
        return f"{self._parent._parent.path_cfg_dir}/{self._parent._parent.name}_locations"

    def path_cfg_get(self, name):
        return f"{self.path_cfg_dir}/{name}.conf"

    @property
    def path_web(self):
        return self._parent._parent.path_web

    @property
    def path_web_default(self):
        return self._parent._parent.path_web_default

    def configure(self):
        """
        in the location obj: config is a server config file of nginx (in text format)
        can use template variables with obj...  (obj is this obj = self, location object is the sub obj)

        :return:
        """
        j.sal.fs.createDir(self.path_cfg_dir)
        # FIXME: https://github.com/threefoldtech/jumpscaleX_core/issues/433
        for location in self.locations_static:
            if not location.path_location.endswith("/"):
                location.path_location += "/"
            content = j.tools.jinja2.file_render(
                path=f"{self._dirpath}/templates/location_static.conf", write=False, obj=location
            )
            j.sal.fs.writeFile(self.path_cfg_get(location.name), content)
            if location.use_jumpscale_weblibs:
                self._add_weblibs(location.path_location)

        for location in self.locations_spa:
            if not location.path_location.endswith("/"):
                location.path_location += "/"
            content = j.tools.jinja2.file_render(
                path=f"{self._dirpath}/templates/location_spa.conf", write=False, obj=location
            )
            j.sal.fs.writeFile(self.path_cfg_get(location.name), content)
            if location.use_jumpscale_weblibs:
                self._add_weblibs(location.path_location)

        for location in self.locations_proxy:
            content = j.tools.jinja2.file_render(
                path=f"{self._dirpath}/templates/location_proxy.conf", write=False, obj=location
            )
            j.sal.fs.writeFile(self.path_cfg_get(location.name), content)

        for location in self.locations_lapis:
            if location.path_location == "":
                location.path_location = self.path_location
            content = j.tools.jinja2.file_render(
                path=f"{self._dirpath}/templates/location_lapis.conf", write=False, obj=location
            )
            j.sal.fs.writeFile(self.path_cfg_get(location.name), content)
            j.sal.process.execute("cd %s;moonc ." % location.path_location)

        for location in self.locations_custom:
            j.sal.fs.writeFile(self.path_cfg_get(location.name), location.config)

    def _add_weblibs(self, path):
        """
        link jumpscale_weblibs repo to the {path}/static
        :param path: path to link to (will copy to {path}/static
        """
        url = "https://github.com/threefoldtech/jumpscaleX_weblibs"
        weblibs_path = j.clients.git.getContentPathFromURLorPath(url, pull=False)

        # copy static dir from repo to the right location
        if "static" in path:
            path = path.rpartition("/")[0]

        static_dir = j.sal.fs.joinPaths(path, "weblibs")

        j.sal.fs.symlink(j.sal.fs.joinPaths(weblibs_path, "static/"), static_dir, True)

    # Helper function
    @staticmethod
    def check_location_exists(locations_obj, new_location_name):
        location = None
        # check if the location already exists or not
        location = [location for location in locations_obj if location.name == new_location_name]
        # if we found the location we return it else we create a new one
        if len(location) != 0:
            return location.pop()
        else:
            new_location = locations_obj.new()
            new_location.name = new_location_name
            return new_location


class Locations(j.baseclasses.object_config_collection):

    _CHILDCLASS = LocationsConfiguration

    def configure(self):
        for item in self.find():
            item.configure()

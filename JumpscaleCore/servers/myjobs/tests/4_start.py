import gevent


def main(self, count=100):
    """
    kosmos -p 'j.servers.myjobs.test("start")'
    """

    def wait_1sec():
        gevent.sleep(1)
        return "OK"

    ids = []
    for x in range(count):
        ids.append(self.schedule(wait_1sec))

    self._workers_gipc_nr_max = 1
    self.workers_subprocess_start()

    res = self.results(ids, timeout=120)

    print(res)

    print("TEST OK")

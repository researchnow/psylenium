class ExpectedPageNotRecognized(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class DriverException(Exception):
    def __init__(self, name, msg):
        super().__init__(f"Encountered {name}: {msg}")


class TimeOutException(Exception):
    def __init__(self, *, by, locator, timeout):
        super().__init__(f"Encountered TimeoutException while waiting for {by} locator [ {locator} ] after {timeout}")

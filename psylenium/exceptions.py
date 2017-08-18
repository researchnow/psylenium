class DriverException(Exception):
    def __init__(self, name, msg):
        super().__init__(f"Encountered {name}: {msg}")

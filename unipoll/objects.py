class DigitalInput:
    def __init__(self):
        self._value = None

    async def update(self):
        """Update internal value by polling syfs"""

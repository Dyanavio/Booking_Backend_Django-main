class RestStatus:
    def __init__(self, isOk: bool, code: int, phrase: str):
        self.isOk = isOk
        self.code = code
        self.phrase = phrase

    def to_dict(self):
        return self.__dict__

class RestResponse:
    def __init__(self, status: RestStatus, data):
        self.status = status
        self.data = data

    def to_dict(self):
        return {
            "status": self.status.to_dict(),
            "data": self.data
        }
import json

class DataToAzAISearch():
     def __init__(self,
        chunksList: list[str]):
         self.chunksList = chunksList

class ValueToAzAISearch():
    def __init__(self,
                  recordId: str,
                    data: DataToAzAISearch,
                      errors,
                        warnings):
        self.recordId = recordId
        self.data = data
        self.errors = errors
        self.warnings = warnings

class ChunkingEmptyRowsResponseBody():
    def __init__(self):
        self.values: list[ValueToAzAISearch] = []
    def addValue(self, value: ValueToAzAISearch):
        self.values.append(value)
    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)
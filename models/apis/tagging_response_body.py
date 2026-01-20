import json

class DataToAzAISearch():
     def __init__(self, folders: list[str],
        storageMetadata: list[str],
        sql_document_id: str):
         self.folders = folders
         self.storageMetadata = storageMetadata
         self.sqlDocumentId = sql_document_id

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

class TaggingResponseBody():
    def __init__(self):
        self.values: list[ValueToAzAISearch] = []
    def addValue(self, value: ValueToAzAISearch):
        self.values.append(value)
    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)
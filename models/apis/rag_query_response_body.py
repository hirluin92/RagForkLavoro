import json

class BestDocument():
    def __init__(self,
                 id: str,
                 sourceFileID: str,
                 fileName: str,
                 tags: str,
                 path: str,
                 similarity: float,
                 chunkText: str,
                 reference: int):
        self.id = id
        self.source_file_id = sourceFileID
        self.filename = fileName
        self.tags = tags
        self.path = path
        self.similarity = similarity
        self.chunk_text = chunkText,
        self.reference = reference
        

class RagQueryResponse():
    def __init__(self, response:str,
                 references: list[int],
                 finishReason: str,
                 links: list[str],
                 referenceSources: bool,
                 contextIds: list[str],
                 context: list[str],
                 bestDocuments: list[BestDocument]) -> None:
        self.response=response
        self.references=references
        self.finish_reason=finishReason
        self.links=links
        self.reference_sources=referenceSources
        self.context_ids=contextIds
        self.context=context
        self.best_documents=bestDocuments
        
    def toJSON(self):
        return json.dumps(self,
                          default=lambda o: o.__dict__,
                          indent=4)
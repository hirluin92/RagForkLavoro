from dataclasses import dataclass
import json

@dataclass
class BestDocument():
    id: str
    source_file_id: str
    filename: str
    tags: str
    path: str
    similarity: float
    chunk_text: str
    reference: int
        

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
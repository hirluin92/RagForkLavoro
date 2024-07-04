import azure.functions as func
from azure.monitor.opentelemetry import configure_azure_monitor
import document_intelligence
import rag_orchestrator
import tagging
import rag_query
import rag_augment_query
import delete_documents
import move_files
import split_data_blob_trigger
import chunking_empty_rows

configure_azure_monitor()


app = func.FunctionApp()

app.register_functions(document_intelligence.bp) 
app.register_functions(delete_documents.bp)
app.register_functions(move_files.bp)
app.register_functions(rag_augment_query.bp)
app.register_functions(rag_orchestrator.bp) 
app.register_functions(rag_query.bp)
app.register_functions(tagging.bp)
app.register_functions(split_data_blob_trigger.bp)
app.register_functions(chunking_empty_rows.bp)


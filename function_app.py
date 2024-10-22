import logging
import azure.functions as func
from azure.monitor.opentelemetry import configure_azure_monitor
import check_status
import document_intelligence
import rag_orchestrator
import metadata_tagging
import rag_query
import rag_augment_query
import move_files
import chunking_empty_rows
import convert_docx_to_md

configure_azure_monitor()
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export").setLevel(logging.WARNING)


app = func.FunctionApp()

#app.register_functions(check_status.bp) 
#app.register_functions(document_intelligence.bp) 
#app.register_functions(move_files.bp)
#app.register_functions(rag_augment_query.bp)
#app.register_functions(rag_orchestrator.bp) 
app.register_functions(rag_query.bp)
#app.register_functions(metadata_tagging.bp)
#app.register_functions(chunking_empty_rows.bp)
#app.register_functions(convert_docx_to_md.bp)

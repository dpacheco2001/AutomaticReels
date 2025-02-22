import asyncio
import os
import re
from datetime import datetime
from tabnanny import verbose

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage, AIMessage

from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal
from langgraph.types import Command

from src.agents.prompts.prompt_templates import grade_prompt, sede_prompt, get_system_good
from src.agents.retrievers.retrievers import get_retriever, retrievers
from src.agents.tools.hultie_tools import test_list, mandar_bases
from src.agents.utils.agent_utils import handle_tool_error, notool_update_sede
from utils.general_utils import print_colored
from src.agents.states.app_state import HultieState, HultieRagState
from src.agents.prompts import prompt_templates
from src.agents.tools import hultie_tools
import random
import pytz

from src import EvolutionAPI, SEDES_CONFIG
from src.agents.prompts.prompt_templates import system_bad

#Instancias
model = ChatOpenAI(model="gpt-4o", temperature=0.1, max_tokens=150)
load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
#model = ChatOpenAI(model="deepseek-chat", api_key=deepseek_api_key,base_url="https://api.deepseek.com",temperature=0.1, max_tokens=250)
#Zona horaria para conseguir la fecha
zona_horaria = pytz.timezone('America/Lima')
api = EvolutionAPI()
#-----------------------------------NODO RETRIEVER(RAG)-----------------------------------------------------------------

def rag_stateinit(state):
    return Command(
        update={"tries_retrieving": 0},
        goto="retrieve"
    )
#Retriever según la sede
def retrieve(state):
    print_colored("---RETRIEVE---", 33)
    question = state["question"]
    print_colored(f"state4: question->{question}", 33)
    sede = state["sede"]
    retriever = get_retriever(sede)
    documents = retriever.invoke(question)
    return Command(
        update= {"documents": documents, "question": question},
        goto="grade_documents"
    )

#-----------------------------------NODO GRADER(RAG)--------------------------------------------------------------------
class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Los documentos son relevantes para la pregunta del usuario, 'si' o 'no'"
    )
structured_llm_grader = model.with_structured_output(GradeDocuments)
retrieval_grader = grade_prompt | structured_llm_grader

def grade_documents(state):
    question = state["question"]
    documents = state["documents"]
    tries = state["tries_retrieving"]
    print_colored(f"---VERIFICANDO RELAVANCIA DE INFORMACIÓN---INTENTO:{tries}", 35)
    filtered_docs = []
    if tries < 3:
        for d in documents:
            score = retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            grade = score.binary_score
            if grade == "si":
                print_colored("---DOCUMENTO RELEVANTE---", 34)
                filtered_docs.append(d)
            else:
                print("---DOCUMENT NO RELEVANTE---", 31)
                continue
    else:
        filtered_docs.append("Sin informacion")
    return Command(
        update={"tries_retrieving": tries + 1, "documents": filtered_docs, "question": question},
        goto="__end__"
    )



#------------------------------------Nodo de herramientas--------------------------------------------------------------

def create_tool_node_with_fallback(tools: list) -> dict:
    """
    Crea un nodo con una lista de herramientas y agrega fallbacks
    para manejar errores en caso de fallos durante la ejecución.
    :param tools: Una lista de herramientas (tools) que se asignarán al nodo.
    :return: Un nodo de herramientas capaz de iterar entre fallbacks para corregirlos
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

#-----------------------------------NODO CLASIFICADOR(RAG)--------------------------------------------------------------
#Clasificador

class SedesOutput(BaseModel):
    datasource: Literal["CERTUS", "UCST", "UPC", "UPCH", "UNCP", "UNI", "UP", "USIL", "UDEP", "UCSUR", "UARM", "ULIMA", "ESAN", "UCAL", "UTEC", "PUCP", "UNMSM", "UNAP", "UCSM", "UTP","SEDE_NO_DISPONIBLE","TODAVIA_NO_ELIGIO_SEDE"] = Field(
        ...,
        description="Dala el input del usuario, clasifica de que sede se debe extraer información",
    )
llm = ChatOpenAI(model="gpt-4o", temperature=0)
model_deepseek = ChatOpenAI(model="deepseek-chat", api_key=deepseek_api_key,base_url="https://api.deepseek.com",temperature=0.1, max_tokens=250)
structured_llm_sedes = llm.with_structured_output(SedesOutput)
sede_chain = sede_prompt | structured_llm_sedes




# ---------------------------------------
class script_agent:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: HultieState, config: RunnableConfig):
        while True:
            messages = state["messages"]
            question = messages[-1].content
            hora_actual = datetime.now(zona_horaria)
            fecha_y_hora_actual = hora_actual.strftime('%Y-%m-%d %H:%M:%S')
            configuration = config.get("configurable", {})

            print_colored(f"sede de donde se esta extrayendo información:{sede}",93)
            if sede in sedes_disponible:
                #rag_result = self.rag_subgraph.invoke({"question":question,"sede":sede})

                rag_result = retrievers.get(sede)
                system = get_system_good(
                    sede=sede,
                    whatsapp=wsp,
                    campus_director=campus_director,
                    urls=urls,
                    link_postulacion=link_postulacion,
                    fecha_limite_postulacion=fecha_limite_postulacion,
                    contexto=rag_result
                )
            else:

                rag_result = "El usuario todavía no ha escogido una sede disponible"
                system = system_bad
            print_colored(f"RAG_RESULT:{rag_result}",36)
            input = {"messages": messages, "user_message": messages[-1].content, "nombre": nombre,
                     "fecha": fecha_y_hora_actual,
                     "inscrito": inscrito, "sede": sede,
                     "system": system,
                     "link_postulacion": link_postulacion}
            state = {**state}

            result = self.runnable.invoke(input)


            if self.verbose: print_colored(f"---STATE 4: state_dudas----\nresult="
                                           f"{result}", 33)
            if result.tool_calls:
                print_colored(f"Llamando función:{result.tool_calls}",34)

            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return Command(
            update= {"messages": result},
        )



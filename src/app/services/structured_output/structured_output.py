from pydantic import BaseModel,validate_call
from main import celery
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from os.path import join,dirname 
import dotenv
from langchain_core.runnables import RunnableLambda
import threading
import traceback
import json
import dotenv

class structuredOutputQuery(BaseModel):
    query: str
class structuredOutputQueries(BaseModel):
    queries: list[structuredOutputQuery]   

class structuredOutputResult(BaseModel):
    status: str
    data: dict={}

class structuredOutputResponces(BaseModel):
    response_code:int
    status: str
    responses: list[structuredOutputResult]=[]



@celery.task(name = "structured_output_v1", bind =True)
@validate_call
def stuructured_output_worker(self, request:structuredOutputQueries, tenant_id:str|None):
    print(request)
    ret = structuredOutputResponces(status="Pending",response_code=200)
    ret.responses = [structuredOutputResult(status = "Pending") for _ in request.queries]
    self.update_state(state = "WorkInProgress", meta = ret.model_dump())
    runner = StructuredOutputRunnner(retVal=ret)
    try:
        threads = []
        for i, req in enumerate(request.queries):
            threads.append(threading.Thread(target=runner.run, args =
                            (self, 
                             self.request.id, 
                             i, 
                             req.model_dump(),)))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        pass
    except Exception as e:
        ret.response_code = 400
        ret.status =  traceback.format_exc()
        return ret.model_dump()
    self.update_state(state = "Complete", meta = ret.model_dump())
    ret.response_code = 200
    ret.status = "Complete"
    return ret.model_dump()

class StructuredOutputRunnner():
    def __init__(self, retVal: structuredOutputResponces):
        dotenv_path = join(dirname(__file__), '.env')
        self.retval = retVal
        dotenv.load_dotenv(dotenv_path)
        AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY",None)
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT",None)
        llm = AzureChatOpenAI(
        openai_api_version="2024-02-01",  # e.g., "2023-12-01-preview"
        azure_deployment="gpt-4o",
        openai_api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint= AZURE_OPENAI_ENDPOINT,
        openai_api_type="azure",
        temperature=0,)
        self.llm = llm
        pass
    @validate_call
    def run(self, app, task_id:str, index, request: structuredOutputQuery):
        chain = self.get_chains()
        res = chain.invoke(request.query)
        response = res.additional_kwargs["function_call"]["arguments"]
        response = json.loads(response)
        timing = response["timing"]
        location = response["location"]
        self.retval.responses[index].data = {"answer": {"timing": timing, "location":location}}


    def get_chains(self):
        llm = self.llm
        function = {
            "name": "extract_information_from_esssays",
            "description": "Read the essay and extract information like the mood of essay and location of the essay.",
            "parameters": {
                "type": "object",
                "required": ["timing", "location"],
                "properties": {
                    "timing":{
                        "type":"string",
                        "description":"when the stories happens."
                    },
                    "location": {
                        "type": "string",
                        "description": "the place where the story of essay goes on. ",
                    },
                },
                
            },
        }
        fc_llm = llm.bind(function_call ={"name":"extract_information_from_esssays"},functions = [function])

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are teacher of essay class and you have to look through the essays your students wrote.",
                ),
                ("human", "{essay}"),
            ]
        )
        chain = RunnableLambda(lambda essay: essay)| prompt| fc_llm
        return chain



    

    
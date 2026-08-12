# Canada API service - Person 1
import requests
import os
from dataclasses import dataclass, field

@dataclass
class ApiResponse:
    success: bool
    result:dict | list | None = None 
    error:str | None = None



BASE_URL= os.environ.get("CANADA_API_BASE_URL","https://open.canada.ca/data/api")

def general_request(endpoint: str, params: dict= None) -> ApiResponse:
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        data= response.json()
    except requests.exceptions.RequestException as e :
        return ApiResponse(success= False, error = f"The Open Canada API was inaccessible: {str(e)}")

    if not data.get("success"):
        return ApiResponse(success= False, error =  data.get("error","An unknown error occurred"))

    return ApiResponse(success=True, result=data["result"])


def get_dataset_details(dataset_id:str) -> ApiResponse:
    return general_request("action/package_show", params={"id":dataset_id})



def list_dataset_ids(limit: int =10) -> ApiResponse:
    response = general_request("action/package_list")
    if response.success:
        response.result = response.result[:limit]
    return response
        

def search_datasets(keyword: str, limit: int = 10) -> ApiResponse:
    response = general_request("action/package_search",params={"q":keyword,"rows":limit})
    if response.success:
        response.result = response.result["results"]
    return response

    

from typing import TypedDict, List, Optional
from .schemas import SicilAnalysisResult

class SicilState(TypedDict):
    company_name: str 
    start_date: Optional[str]
    end_date: Optional[str]
    pdf_paths: List[str]        
    ocr_text: Optional[str]     
    analysis: Optional[SicilAnalysisResult] 
    error: Optional[str]        
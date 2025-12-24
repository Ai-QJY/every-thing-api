from typing import Optional
from services.base_ai_service import BaseAIService
from services.grok_service import GrokService
from services.session_manager import SessionManager

class AIServiceFactory:
    """
    Factory for creating AI service instances
    """
    
    @staticmethod
    def create_service(service_name: str, session_manager: SessionManager) -> Optional[BaseAIService]:
        """
        Create an AI service instance based on the service name
        """
        service_name = service_name.lower()
        
        if service_name == "grok":
            return GrokService(session_manager)
        
        # Add more services here as needed
        # elif service_name == "xai":
        #     return XaiService(session_manager)
        
        return None
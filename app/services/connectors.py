from typing import List, Dict, Any, Optional
from datetime import datetime
import random

class IntegrationStatus:
    def __init__(self, provider: str, connected: bool = False, last_sync: datetime = None):
        self.provider = provider
        self.connected = connected
        self.last_sync = last_sync
        self.status = "active" if connected else "disconnected"

# In-memory store for simulation (Phase 7 MVP)
# In production, this would be in the 'integrations' database table
MOCK_INTEGRATIONS_DB = {
    "stripe": IntegrationStatus("Stripe", False),
    "plaid": IntegrationStatus("Plaid", False),
    "salesforce": IntegrationStatus("Salesforce", False),
    "quickbooks": IntegrationStatus("QuickBooks", False),
    "yahoo_finance": IntegrationStatus("Yahoo Finance", True),  # Market data - always available
}

class ConnectorService:
    """
    The Nervous System Core.
    Manages connections to external financial organs.
    """
    
    def get_all_integrations(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": k,
                "name": v.provider,
                "connected": v.connected,
                "last_sync": v.last_sync.isoformat() if v.last_sync else None,
                "status": v.status,
                "icon": f"/icons/{k}.png" # Frontend handles icons
            }
            for k, v in MOCK_INTEGRATIONS_DB.items()
        ]

    def connect_provider(self, provider_id: str, api_key: str) -> Dict[str, Any]:
        """
        Simulates an OAuth handshake or API Key validation.
        """
        if provider_id not in MOCK_INTEGRATIONS_DB:
            return {"status": "error", "message": "Unknown provider"}
            
        # Simulate Network Delay & Validation
        # In real world: validate_api_key(api_key)
        
        integration = MOCK_INTEGRATIONS_DB[provider_id]
        integration.connected = True
        integration.last_sync = datetime.now()
        integration.status = "active"
        
        return {
            "status": "success", 
            "message": f"Successfully connected to {integration.provider}",
            "data": {
                "id": provider_id,
                "connected": True,
                "last_sync": integration.last_sync.isoformat()
            }
        }

    def disconnect_provider(self, provider_id: str) -> Dict[str, Any]:
        if provider_id not in MOCK_INTEGRATIONS_DB:
            return {"status": "error", "message": "Unknown provider"}
            
        integration = MOCK_INTEGRATIONS_DB[provider_id]
        integration.connected = False
        integration.status = "disconnected"
        
        return {"status": "success", "message": f"Disconnected {integration.provider}"}

    def trigger_sync(self, provider_id: str) -> Dict[str, Any]:
        """
        Forces a data pull from the provider.
        """
        if provider_id not in MOCK_INTEGRATIONS_DB or not MOCK_INTEGRATIONS_DB[provider_id].connected:
             return {"status": "error", "message": "Provider not connected"}
             
        # Simulate syncing N transactions
        new_txns = random.randint(5, 50)
        MOCK_INTEGRATIONS_DB[provider_id].last_sync = datetime.now()
        
        return {
            "status": "success",
            "message": f"Synced {new_txns} new transactions from {MOCK_INTEGRATIONS_DB[provider_id].provider}",
            "synced_count": new_txns
        }

connector_service = ConnectorService()

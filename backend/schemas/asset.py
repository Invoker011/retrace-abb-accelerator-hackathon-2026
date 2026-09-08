"""Asset and topology relationship schemas."""
from typing import Dict, Optional
from pydantic import BaseModel, Field

class Asset(BaseModel):
    id: str
    name: str
    tag: str
    type: str
    plant_area: str = Field(..., alias="plantArea")
    status: str  # Normal, Warning, Tripped, Offline
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    criticality: str  # Critical, High, Medium, Low
    specs: Dict[str, str] = Field(default_factory=dict)
    description: str

    class Config:
        populate_by_name = True

class AssetRelationship(BaseModel):
    id: str
    source_asset_id: str = Field(..., alias="sourceAssetId")
    target_asset_id: str = Field(..., alias="targetAssetId")
    relation_type: str = Field(..., alias="relationType")  # powers, drives, monitored by, supplies, controls
    description: str

    class Config:
        populate_by_name = True

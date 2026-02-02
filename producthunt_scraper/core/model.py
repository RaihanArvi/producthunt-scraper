from pydantic import BaseModel
from typing import List, Optional

class Link(BaseModel):
    type: str
    href: str

class TeamPage(BaseModel):
    about: str
    links: List[Link]

class TeamMember(BaseModel):
    name: str
    role: str
    href: str

    team_page: Optional[TeamPage]

class BuiltWithProduct(BaseModel):
    name: str
    tagline: str
    categories: List[str]
    ph_link: str

class BuiltWithProduct(BaseModel):
    name: str
    tagline: str
    categories: List[str]
    ph_link: str

class BuiltWithGroup(BaseModel):
    group_name: str
    products: List[BuiltWithProduct]

class BuiltWithGroup(BaseModel):
    group_name: str
    products: List[BuiltWithProduct]

class ProductPage(BaseModel):
    product_name: str
    product_description: str
    categories: List[str]
    website_link: str

    team_members: Optional[List[TeamMember]]
    built_with: Optional[List[BuiltWithGroup]]

class Product(BaseModel):
    name: str
    tagline: str
    topics: List[str]
    ph_url: str

    product_page: Optional[ProductPage]

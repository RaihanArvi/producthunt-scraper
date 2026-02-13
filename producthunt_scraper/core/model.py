"""
Pydantic models for Product Hunt scraped data.

Defines Link, TeamPage, TeamMember, BuiltWithProduct, BuiltWithGroup,
ProductPage, and Product used by parser, script, BigQuery, and JSON output.
"""
from pydantic import BaseModel
from typing import List, Optional


class Link(BaseModel):
    """Single link on a team/maker page (e.g. Twitter, LinkedIn). type + href."""

    type: str
    href: str


class TeamPage(BaseModel):
    """Maker/team member about section: about text and list of links."""

    about: str
    links: List[Link]


class TeamMember(BaseModel):
    """Maker on a product: name, role, href to profile, optional team_page."""

    name: str
    role: str
    href: str

    team_page: Optional[TeamPage]


class BuiltWithProduct(BaseModel):
    """Product listed in a Built With group: name, tagline, categories, ph_link."""

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
    """Built With section group: group_name and list of BuiltWithProduct."""

    group_name: str
    products: List[BuiltWithProduct]

class BuiltWithGroup(BaseModel):
    group_name: str
    products: List[BuiltWithProduct]


class ProductPage(BaseModel):
    """Full product page: name, description, categories, website, team_members, built_with."""

    product_name: str
    product_description: str
    categories: List[str]
    website_link: str

    team_members: Optional[List[TeamMember]]
    built_with: Optional[List[BuiltWithGroup]]


class Product(BaseModel):
    """Leaderboard product: name, tagline, topics, ph_url; optional date (YYYY-MM-DD) and product_page."""

    name: str
    tagline: str
    topics: List[str]
    ph_url: str
    date: Optional[str] = None  # YYYY-MM-DD, when the product was scraped

    product_page: Optional[ProductPage]

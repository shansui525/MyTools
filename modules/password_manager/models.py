# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Literal

Category = Literal["website", "computer", "other"]


@dataclass
class CredentialEntry:
    id: int
    title: str
    category: Category
    target: str
    username: str
    password: str
    notes: str
    created_at: str
    updated_at: str


@dataclass
class CredentialListItem:
    id: int
    title: str
    category: Category
    target: str
    created_at: str
    updated_at: str

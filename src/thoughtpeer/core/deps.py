from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import Depends

from .config import Settings, get_settings
from .database import get_db

DbDep = Annotated[aiosqlite.Connection, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

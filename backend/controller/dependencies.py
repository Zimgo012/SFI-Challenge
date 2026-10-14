from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from service.database import get_session

Database = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]

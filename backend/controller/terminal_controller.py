from fastapi import APIRouter, WebSocket

from controller.dependencies import Database, Limit, Offset
from schema.api import Page, TerminalDetail, TerminalView
from schema.terminal_status import TerminalStatus
from service import dashboard
from service.terminal_status import stream_terminal_statuses, terminal_statuses

router = APIRouter(prefix='/api/terminals', tags=['Terminals'])


@router.get('/status', response_model=list[TerminalStatus])
def all_terminal_statuses(session: Database) -> list[TerminalStatus]:
    return terminal_statuses(session)


@router.websocket('/status/ws')
async def subscribe_terminal_statuses(websocket: WebSocket, session: Database):
    await stream_terminal_statuses(websocket, session.get_bind())


@router.get('', response_model=Page[TerminalView])
def terminals(session: Database, limit: Limit = 50, offset: Offset = 0):
    return dashboard.list_terminals(session, limit, offset)


@router.get('/{code}', response_model=TerminalDetail)
def terminal(code: str, session: Database):
    return dashboard.terminal_detail(session, code)

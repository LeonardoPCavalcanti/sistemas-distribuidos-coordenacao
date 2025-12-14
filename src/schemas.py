from pydantic import BaseModel


class Message(BaseModel):
    sender_id: int
    message_id: str
    timestamp: int
    content: str


class Ack(BaseModel):
    message_id: str
    process_id: int


class SCRequest(BaseModel):
    request_ts: int
    process_id: int

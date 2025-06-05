from pydantic import BaseModel

class FeedURLRequest(BaseModel):
    feed_url: str
    client_id: str = "default"

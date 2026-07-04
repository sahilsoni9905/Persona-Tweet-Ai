from pydantic import BaseModel


class ReferencePost(BaseModel):
    id: str
    text: str
    note: str = ""


class TweetUrlRequest(BaseModel):
    url: str
    note: str = ""


class AddPostRequest(BaseModel):
    text: str


class AddReplyRequest(BaseModel):
    text: str


class ReplyToTweetRequest(BaseModel):
    tweet_url: str = ""
    tweet_text: str = ""


class SendReplyRequest(BaseModel):
    text: str
    hashtags: list[str] = []
    in_reply_to_id: str = ""
    mention_username: str = ""


class PostRequest(BaseModel):
    text: str
    hashtags: list[str] = []


class SettingsUpdate(BaseModel):
    style_score_threshold: float | None = None
    max_retries: int | None = None
    post_mode: str | None = None


class SchedulerStart(BaseModel):
    times_per_day: int = 5
    interval_seconds: int | None = None


class ReplySchedulerStart(BaseModel):
    interval_minutes: int = 30


class FeedReplySchedulerStart(BaseModel):
    interval_minutes: int = 45
    max_per_day: int = 8
    active_hours_start: int = 9
    active_hours_end: int = 23

from pydantic import BaseModel


class ErrorRead(BaseModel):
    detail: str
    code: str


def get_error_responses(*status_codes: int) -> dict[int | str, dict]:
    return {status_code: {"model": ErrorRead} for status_code in status_codes}

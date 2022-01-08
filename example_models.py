import datetime
import enum
import typing

import arrow
import pydantic


class TextEnum(str, enum.Enum):
    first = "first"
    second = "second"
    third = "third"


class ExampleRequest(pydantic.BaseModel):
    text: str = pydantic.Field(
        title="Some field with text",
        max_length=255,
    )
    choices_text: TextEnum = pydantic.Field(
        title="Some field with choices",
    )
    number: int = pydantic.Field(
        title="Some random number",
        ge=0,
        le=999999,
    )
    some_date: datetime.date = pydantic.Field(
        title="Some random date",
    )
    list_field: list[str] = pydantic.Field(
        title="List field",
    )

    class Config:
        use_enum_values = True

    @pydantic.validator("some_date")
    def check_if_date_valid(cls, value):
        if (arrow.now().date() - value).total_seconds() < 0:
            raise ValueError('Some validation error')
        return value


class GetExampleResponse(pydantic.BaseModel):
    number: int
    choices_text: typing.Union[TextEnum, None] = pydantic.Field(
        title="Some field with choices",
    )

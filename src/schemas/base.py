from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseRequestModel(BaseModel):
    """Allows CamelCase as an input as well as default snake_case."""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class BaseResponseModel(BaseModel):
    """Allows to populate model attributes from ORM objects or dictionaries."""
    model_config = ConfigDict(from_attributes=True)

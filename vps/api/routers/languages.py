from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api import pydantic_models as models
from api.actions.users import get_current_user
from db.dals.languages import LanguagesDAL
from db.session import get_db

router = APIRouter()


@router.get(
    path="/",
    tags=["Languages"],
    description="Get list of languages.",
    response_model=models.LanguagesList,
    responses={401: {"description": "Not authenticated"}},
)
async def get_languagess_list(
    request: Request,
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        language_dal = LanguagesDAL(db)
        languages = await language_dal.get_list()

    languages_list = []

    for item in languages:
        languages_list.append(
            models.LanguageInfo(
                id=item.id,
                name=item.lang_name,
                source=item.source,
                target=item.target
            )
        )

    return models.LanguagesList(languages=languages_list)

"""
Project service: create, list, update, delete projects.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate, _slugify


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)

    async def create(self, data: ProjectCreate, owner: User) -> ProjectResponse:
        slug = data.slug or _slugify(data.name)

        # Ensure slug is unique — append owner's id suffix if taken
        existing = await self.repo.get_by_slug(slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with slug '{slug}' already exists. "
                       "Provide a different slug or rename your project.",
            )

        project = await self.repo.create(
            owner_id=owner.id,
            name=data.name,
            slug=slug,
            description=data.description,
        )
        return ProjectResponse.model_validate(project)

    async def list(self, owner: User) -> list[ProjectResponse]:
        projects = await self.repo.list_by_owner(owner.id)
        return [ProjectResponse.model_validate(p) for p in projects]

    async def get(self, project_id: uuid.UUID, owner: User) -> ProjectResponse:
        project = await self._get_owned(project_id, owner.id)
        return ProjectResponse.model_validate(project)

    async def update(self, project_id: uuid.UUID, data: ProjectUpdate, owner: User) -> ProjectResponse:
        project = await self._get_owned(project_id, owner.id)
        updates = data.model_dump(exclude_unset=True)
        if updates:
            project = await self.repo.update(project, **updates)
        return ProjectResponse.model_validate(project)

    async def delete(self, project_id: uuid.UUID, owner: User) -> None:
        project = await self._get_owned(project_id, owner.id)
        await self.repo.delete(project)

    async def _get_owned(self, project_id: uuid.UUID, owner_id: uuid.UUID):
        """Fetch project and verify ownership. Raises 404 if not found or not owned."""
        project = await self.repo.get_by_id(project_id)
        if not project or not project.is_active or project.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

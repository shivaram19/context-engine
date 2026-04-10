"""
Permission service — filter chunks by user permissions.

MVP: tenant isolation only (all org members see all org docs).
Extension point: fine-grained permissions added here later without touching QueryService.
"""

import logging

from domain.models import Chunk

logger = logging.getLogger(__name__)


class PermissionService:
    """
    Filter chunks by user permissions.

    MVP rule: return all chunks where chunk.org_id == org_id.
    This ensures tenant isolation at the service layer (RLS protects at DB layer).

    Extension point: fine-grained permissions (user roles, document-level ACLs)
    can be added here in the future without changing QueryService.
    """

    def filter(self, user_id: str, org_id: str, chunks: list[Chunk]) -> list[Chunk]:
        """
        Filter chunks by user permissions.

        Args:
            user_id: User requesting the chunks (unused in MVP)
            org_id: Organization ID for tenant isolation
            chunks: Retrieved chunks from vector store

        Returns:
            Filtered chunks that user is allowed to access
        """
        if not chunks:
            return []

        allowed = []

        for chunk in chunks:
            # MVP rule: tenant isolation — chunk must belong to same org
            if chunk.org_id != org_id:
                logger.warning(
                    f"[PermissionService] RLS FAILURE: chunk {chunk.id} has org_id={chunk.org_id} "
                    f"but request is for org_id={org_id}. This should never happen."
                )
                continue

            # In MVP, all org members see all org docs
            # Extension point: check user roles, document ACLs, etc. here
            allowed.append(chunk)

        logger.debug(
            f"[PermissionService] filtered {len(chunks)} chunks → {len(allowed)} allowed for user {user_id}"
        )
        return allowed

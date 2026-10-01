"""Importe tous les modèles pour qu'Alembic (autogenerate) et Base.metadata
les voient tous -- sans ça, une table absente de cette liste est invisible
aux migrations."""
from .application import Application
from .beta_invite import BetaInvite
from .cv_content import CvFile, Experience, Role, RoleExperienceBullet, RoleProject
from .discovery import DiscoverySource, Posting
from .email_account import EmailAccount
from .onboarding import CvUpload, CvUploadExtraction, DraftSourceUpload, ExtractedProfileDraft
from .user import Profile, User

__all__ = [
    "Application",
    "BetaInvite",
    "CvFile",
    "Experience",
    "Role",
    "RoleExperienceBullet",
    "RoleProject",
    "DiscoverySource",
    "Posting",
    "EmailAccount",
    "CvUpload",
    "CvUploadExtraction",
    "DraftSourceUpload",
    "ExtractedProfileDraft",
    "Profile",
    "User",
]

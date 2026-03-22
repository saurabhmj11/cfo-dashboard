from sqlalchemy.orm import Session
from app.models import db_models, schemas

def create_tenant(db: Session, tenant: schemas.TenantCreate):
    """
    Create a new organization/tenant.
    """
    db_tenant = db_models.Tenant(
        name=tenant.name,
        plan_type=tenant.plan_type
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant

def get_tenant(db: Session, tenant_id: int):
    return db.query(db_models.Tenant).filter(db_models.Tenant.id == tenant_id).first()

def get_tenant_by_name(db: Session, name: str):
    return db.query(db_models.Tenant).filter(db_models.Tenant.name == name).first()

def assign_user_to_tenant(db: Session, user_id: int, tenant_id: int):
    user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if user:
        user.tenant_id = tenant_id
        db.commit()
        db.refresh(user)
    return user

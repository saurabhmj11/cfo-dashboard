import sys
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import db_models, schemas
from app.services import tenant_service, auth_service

def verify_tenancy():
    db = SessionLocal()
    try:
        print("--- Verifying Multi-Tenancy ---")
        
        # 1. Create two tenants
        t1 = tenant_service.get_tenant_by_name(db, "Org_A") or \
             tenant_service.create_tenant(db, schemas.TenantCreate(name="Org_A"))
        t2 = tenant_service.get_tenant_by_name(db, "Org_B") or \
             tenant_service.create_tenant(db, schemas.TenantCreate(name="Org_B"))
        
        print(f"Tenants: {t1.name} (ID: {t1.id}), {t2.name} (ID: {t2.id})")
        
        # 2. Create users for each tenant
        def get_or_create_user(username, tenant_id):
            user = db.query(db_models.User).filter(db_models.User.username == username).first()
            if not user:
                user = db_models.User(
                    username=username,
                    email=f"{username}@example.com",
                    hashed_password="mock_hash",
                    tenant_id=tenant_id
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

        u1 = get_or_create_user("user_a", t1.id)
        u2 = get_or_create_user("user_b", t2.id)
        
        print(f"Users: {u1.username} in {t1.name}, {u2.username} in {t2.name}")

        # 3. Create a dataset for Tenant A
        d1 = db.query(db_models.Dataset).filter(db_models.Dataset.filename == "data_a.csv").first()
        if not d1:
            d1 = db_models.Dataset(
                filename="data_a.csv",
                file_path="/tmp/data_a.csv",
                user_id=u1.id,
                tenant_id=t1.id
            )
            db.add(d1)
            db.commit()
            db.refresh(d1)
        
        print(f"Dataset created for {t1.name}: {d1.filename}")

        # 4. Mock a request as User B and try to access Dataset A
        # (This simulates the logic in our routers)
        def can_access(user, dataset_id):
            dataset = db.query(db_models.Dataset).filter(
                db_models.Dataset.id == dataset_id,
                db_models.Dataset.tenant_id == user.tenant_id
            ).first()
            return dataset is not None

        access_a = can_access(u1, d1.id)
        access_b = can_access(u2, d1.id)
        
        print(f"Tenant A user accessing Dataset A: {'SUCCESS' if access_a else 'FAILED'}")
        print(f"Tenant B user accessing Dataset A: {'BLOCKED (Correct)' if not access_b else 'DANGER: LEAK DETECTED'}")
        
        if access_a and not access_b:
            print("\n✅ Multi-Tenancy Isolation Verified!")
        else:
            print("\n❌ Multi-Tenancy Isolation FAILED!")

    finally:
        db.close()

if __name__ == "__main__":
    verify_tenancy()

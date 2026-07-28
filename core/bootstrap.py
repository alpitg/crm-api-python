from core.seed.permissions import seed_role_permissions
from core.seed.roles import seed_default_roles
from core.seed.users import seed_admin_user


async def init_database():
    print("🚀 Initializing database setup...")

    try:
        await seed_role_permissions()
        await seed_default_roles()
        await seed_admin_user()
        print("🎉 Database initialization completed successfully.")

    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        raise


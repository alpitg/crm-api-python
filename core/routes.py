
from fastapi import FastAPI

from app.routes import customer, orders, ping, user
from app.routes.administration import organization_units, role_permissions, roles
from app.routes.catalog import products
from app.routes.master import frame_types, glass_types, misc_charges, mount_types, order_status

def setup_router(app: FastAPI) -> None:
    """
    Register all routes with the FastAPI application.
    """
    app.include_router(user.router, prefix="/api")
    app.include_router(ping.router, prefix="/api/ping")

    #region Administration
    app.include_router(organization_units.router, prefix="/api/organization-units", tags=["Organization Units"])
    app.include_router(roles.router, prefix="/api/roles", tags=["Roles"])
    app.include_router(role_permissions.router, prefix="/api/roles/permissions", tags=["Roles-permissions"])
    # app.include_router(users.router, prefix="/api/users", tags=["Users"])
    #endregion

    #region Catalog
    app.include_router(products.router, prefix="/api/products", tags=["Products"])
    app.include_router(customer.router, prefix="/api/customer", tags=["Customer"])
    app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
    #endregion


    # region master routes
    app.include_router(frame_types.router, prefix="/api/master/frame_types", tags=["Master - Frame Types"])
    app.include_router(glass_types.router, prefix="/api/master/glass_types", tags=["Master - Glass Types"])
    app.include_router(misc_charges.router, prefix="/api/master/misc_charges", tags=["Master - Misc Charges"])
    app.include_router(mount_types.router, prefix="/api/master/mount_types", tags=["Master - Mount Types"])
    app.include_router(order_status.router, prefix="/api/master/order_status", tags=["Master - Order Status"])
    # endregion

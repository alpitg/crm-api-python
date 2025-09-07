
from fastapi import FastAPI

from app.modules.administration.auth import auth_routes
from app.modules.administration.organisation_units import organisation_units_routes
from app.modules.administration.role import role_permissions_routes, role_routes
from app.modules.administration.user import user_routes
from app.modules.customer import customer_route
from app.modules.master.frame_types import frame_type_routes
from app.modules.master.glass_type import glass_type_routes
from app.modules.master.misc_charges import misc_charges_routes
from app.modules.master.mount_type import mount_type_routes
from app.modules.master.order_status import order_status_routes
from app.modules.orders import orders_route
from app.modules.administration import ping
from app.modules.products import products_route

def setup_router(app: FastAPI) -> None:
    """
    Register all routes with the FastAPI application.
    """
    app.include_router(ping.router, prefix="/api/ping")

    #region Administration
    app.include_router(auth_routes.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(organisation_units_routes.router, prefix="/api/organization-units", tags=["Organization Units"])
    app.include_router(role_routes.router, prefix="/api/roles", tags=["Roles"])
    app.include_router(role_permissions_routes.router, prefix="/api/roles-permissions", tags=["Roles-permissions"])
    app.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
    #endregion

    #region Catalog
    app.include_router(products_route.router, prefix="/api/products", tags=["Products"])
    app.include_router(customer_route.router, prefix="/api/customer", tags=["Customer"])
    app.include_router(orders_route.router, prefix="/api/orders", tags=["Orders"])
    #endregion


    # region master routes
    app.include_router(frame_type_routes.router, prefix="/api/master/frame_types", tags=["Master - Frame Types"])
    app.include_router(glass_type_routes.router, prefix="/api/master/glass_types", tags=["Master - Glass Types"])
    app.include_router(misc_charges_routes.router, prefix="/api/master/misc_charges", tags=["Master - Misc Charges"])
    app.include_router(mount_type_routes.router, prefix="/api/master/mount_types", tags=["Master - Mount Types"])
    app.include_router(order_status_routes.router, prefix="/api/master/order_status", tags=["Master - Order Status"])
    # endregion

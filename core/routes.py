
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
from app.modules.invoice import invoice_routes
from app.modules.products.public import product_public_route
from app.modules.blob import upload_router

def setup_router(app: FastAPI) -> None:
    """
    Register all routes with the FastAPI application.
    """
    #region Public

    app.include_router(ping.router, prefix="/ping", tags=["Public"])

    app.include_router(product_public_route.public_router, prefix="/store", tags=["Public"])

    app.include_router(upload_router.router, prefix="/upload", tags=["Public"])
    #endregion



    #region Meal Planner
    from app.modules.meal_planner import meal_planner_routes
    app.include_router(meal_planner_routes.router, prefix="/meal-planner", tags=["Meal Planner"])

    #region Administration
    app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
    app.include_router(organisation_units_routes.router, prefix="/organization-units", tags=["Organization Units"])
    app.include_router(role_routes.router, prefix="/roles", tags=["Roles"])
    app.include_router(role_permissions_routes.router, prefix="/roles-permissions", tags=["Roles-permissions"])
    app.include_router(user_routes.router, prefix="/users", tags=["Users"])
    #endregion

    #region Catalog
    app.include_router(products_route.router, prefix="/products", tags=["Products"])
    app.include_router(customer_route.router, prefix="/customer", tags=["Customer"])
    app.include_router(orders_route.router, prefix="/orders", tags=["Orders"])
    #endregion

    #region Invoice
    app.include_router(invoice_routes.router, prefix="/invoices", tags=["Invoices"])
    #endregion


    # region master routes
    app.include_router(frame_type_routes.router, prefix="/master/frame_types", tags=["Master - Frame Types"])
    app.include_router(glass_type_routes.router, prefix="/master/glass_types", tags=["Master - Glass Types"])
    app.include_router(misc_charges_routes.router, prefix="/master/misc_charges", tags=["Master - Misc Charges"])
    app.include_router(mount_type_routes.router, prefix="/master/mount_types", tags=["Master - Mount Types"])
    app.include_router(order_status_routes.router, prefix="/master/order_status", tags=["Master - Order Status"])
    # endregion

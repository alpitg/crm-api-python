
from fastapi import FastAPI

from app.routes import customer, orders, products, user
from app.routes.master import frame_types, glass_types, misc_charges, mount_types, order_status

class DeafultController:
    """
    DeafultController handles the routing for master data management,
    including frame types and glass types.
    """

    def __init__(self, app: FastAPI):
        self.app = app

    def register_routes(self):
        """
        Register all master routes with the FastAPI application.
        """
        self.app.include_router(user.router, prefix="/api")

        # region master routes
        self.app.include_router(frame_types.router, prefix="/api/master/frame_types", tags=["Master - Frame Types"])
        self.app.include_router(glass_types.router, prefix="/api/master/glass_types", tags=["Master - Glass Types"])
        self.app.include_router(misc_charges.router, prefix="/api/master/misc_charges", tags=["Master - Misc Charges"])
        self.app.include_router(mount_types.router, prefix="/api/master/mount_types", tags=["Master - Mount Types"])
        self.app.include_router(order_status.router, prefix="/api/master/order_status", tags=["Master - Order Status"])
        # endregion

        self.app.include_router(customer.router, prefix="/api/customer", tags=["Customer"])
        self.app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
        self.app.include_router(products.router, prefix="/api/products", tags=["Products"])



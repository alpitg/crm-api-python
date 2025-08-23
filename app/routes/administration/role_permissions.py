from fastapi import APIRouter
from typing import List

from app.schemas.administration.roles.role_permissions import RolePermissionOut
from core.sanitize import stringify_object_ids
from app.db.mongo import db

router = APIRouter()
collection = db["role_permissions"]


# ✅ 1. Get all role permissions
@router.get("/", response_model=List[RolePermissionOut])
async def get_role_permissions():
    cursor = collection.find({})
    results = []
    async for doc in cursor:
        results.append(stringify_object_ids(doc))
    return results


# ✅ 2. Reset role permissions (delete + insert fresh data)
@router.post("/reset", response_model=dict)
async def reset_role_permissions():
    # Clean existing permissions
    await collection.delete_many({})

    # Fresh data (you can move this to a config or constants file)
    permissionItems = [
        {
            "name": "Pages",
            "displayName": "Pages",
            "description": "Access to all pages",
            "parentName": "",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration",
            "displayName": "Administration",
            "description": "Access to all Administration pages",
            "parentName": "Pages",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.OrganizationUnits",
            "displayName": "Organization Units",
            "description": "Access to organization units",
            "parentName": "Pages.Administration",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.OrganizationUnits.Detail",
            "displayName": "Organization Unit Details",
            "description": "View organization unit details",
            "parentName": "Pages.Administration.OrganizationUnits",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.OrganizationUnits.Create",
            "displayName": "Create Organization Unit",
            "description": "Create new organization units",
            "parentName": "Pages.Administration.OrganizationUnits",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.OrganizationUnits.Edit",
            "displayName": "Edit Organization Unit",
            "description": "Edit existing organization units",
            "parentName": "Pages.Administration.OrganizationUnits",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.OrganizationUnits.Delete",
            "displayName": "Delete Organization Unit",
            "description": "Delete organization units",
            "parentName": "Pages.Administration.OrganizationUnits",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Roles",
            "displayName": "Roles",
            "description": "Manage application roles",
            "parentName": "Pages.Administration",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Roles.Create",
            "displayName": "Create Role",
            "description": "Create new role",
            "parentName": "Pages.Administration.Roles",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Roles.Edit",
            "displayName": "Edit Role",
            "description": "Edit role",
            "parentName": "Pages.Administration.Roles",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Roles.Delete",
            "displayName": "Delete Role",
            "description": "Delete existing role",
            "parentName": "Pages.Administration.Roles",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Users",
            "displayName": "Users",
            "description": "Manage users and their permissions",
            "parentName": "Pages.Administration",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Users.Create",
            "displayName": "Create User",
            "description": "Create new user",
            "parentName": "Pages.Administration.Users",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Users.Edit",
            "displayName": "Edit User",
            "description": "Edit user",
            "parentName": "Pages.Administration.Users",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Administration.Users.Delete",
            "displayName": "Delete User",
            "description": "Delete existing user",
            "parentName": "Pages.Administration.Users",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Catalog",
            "displayName": "Catalog",
            "description": "Manage access for Catalog",
            "parentName": "Pages",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Catalog.Product",
            "displayName": "Products",
            "description": "Manage products in catalog",
            "parentName": "Pages.Catalog",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Catalog.ProductCategory",
            "displayName": "Product Categories",
            "description": "Manage product categories",
            "parentName": "Pages.Catalog",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Sales",
            "displayName": "Sales",
            "description": "Manage access for Sales",
            "parentName": "Pages",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Sales.Order",
            "displayName": "Orders",
            "description": "Manage sales orders",
            "parentName": "Pages.Sales",
            "isGrantedByDefault": False,
        },
        {
            "name": "Pages.Sales.Customers",
            "displayName": "Customers",
            "description": "Manage sales customers",
            "parentName": "Pages.Sales",
            "isGrantedByDefault": False,
        },
    ]

    # Insert fresh permissions
    await collection.insert_many(permissionItems)

    return {"message": "Role permissions reset successfully", "count": len(permissionItems)}

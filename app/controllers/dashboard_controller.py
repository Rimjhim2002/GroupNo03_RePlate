from app.models.user import User
async def get_restaurant_dashboard(user: User) -> dict:
    # TODO: replace with real numbers once FoodListing/Transaction exist
    return {
        "user_id": str(user.id),
        "business_name": user.business_name,
        "active_listings":0,
        "active_reservations":0,
        "completed_transactions":0,
        "revenue_recovered":0.0,
        "waste_value_avoided":0.0,
        "meals_donated": 0
    }

async def get_consumer_dashboard(user: User) -> dict:
    return {
        "user_id": str(user.id),
        "active_reservations":0,
        "completed_transactions":0,
        "meals_received":0,
        "money_saved": 0.0
    }

async def get_ngo_dashboard(user: User) -> dict:
    return {
        "user_id":str(user.id),
        "organization_name":user.organization_name,
        "active_reservations": 0,
        "completed_transactions":0,
        "meals_claimed":0,
        "donations_fulfilled":0
    }

async def get_admin_dashboard(user: User) -> dict:
    total_users = await User.find_all().count()
    pending =await User.find(User.verification_status == "pending").count()
    return {
        "user_id":str(user.id),
        "total_users":total_users,
        "pending_verifications":pending
    }
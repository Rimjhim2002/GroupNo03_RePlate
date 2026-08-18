from enum import Enum
class ListingType(str,Enum):
    SALE = "sale"
    DONATION = "donation"
class ListingStatus(str,Enum):
    AVAILABLE ="available"
    RESERVED ="reserved"
    SOLD_DONATED ="sold_donated"
    COMPLETED ="completed"
    EXPIRED ="expired"
class WaitlistStatus(str, Enum):
    WAITING ="waiting"
    NOTIFIED ="notified"
    CONVERTED ="converted"
    EXPIRED ="expired"

class TransactionType(str,Enum):
    SALE ="sale"
    DONATION ="donation"


class TransactionStatus(str,Enum):
    RESERVED ="reserved"
    DONATED ="donated"
    COMPLETED ="completed"
    CANCELLED ="cancelled"


class NotificationType(str,Enum):
    DONATION_AVAILABLE ="donation_available"
    WAITLIST_NEXT ="waitlist_next"
    RATING_RECEIVED ="rating_received"
    EXPIRY_ALERT ="expiry_alert"

class ReportType(str,Enum):
    IMPACT_REPORT ="impact_report"
    PLATFORM_REPORT ="platform_report"
class RecommendationType(str, Enum):
    APPLY_DISCOUNT ="apply_discount"
    CONVERT_TO_DONATION ="convert_to_donation"
    REMOVE_LISTING ="remove_listing"
    FLAG_DUPLICATE ="flag_duplicate"
class ReportFormat(str, Enum):
    PDF ="pdf"
    CSV ="csv"
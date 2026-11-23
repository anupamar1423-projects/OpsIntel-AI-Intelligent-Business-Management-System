from .models import Membership
from .org import current_org
from .models import Notification

def workspace(request):
    if not request.user.is_authenticated:
        return {"active_organization": None, "user_organizations": [], "unread_notifications": 0, "active_role": None}
    org=current_org(request)
    return {
        "active_organization": org,
        "user_organizations": Membership.objects.filter(user=request.user).select_related("organization"),
        "unread_notifications": Notification.objects.filter(organization=org,recipient=request.user,read_at__isnull=True).count() if org else 0,
        "active_role": Membership.objects.filter(user=request.user,organization=org).values_list("role",flat=True).first() if org else None,
    }

from .models import Membership
def current_org(request):
 if not request.user.is_authenticated:
  return None
 memberships=Membership.objects.filter(user=request.user).select_related("organization")
 active_id=request.session.get("active_org_id")
 if active_id:
  selected=memberships.filter(organization_id=active_id).first()
  if selected:
   return selected.organization
  request.session.pop("active_org_id",None)
 selected=memberships.first()
 if selected:
  request.session["active_org_id"]=selected.organization_id
  return selected.organization
 return None

from functools import wraps

from django.http import HttpResponseForbidden

from .models import AuditEvent, Membership


def member_for(user, organization):
    return Membership.objects.filter(user=user, organization=organization).first()


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            from .org import current_org
            org = current_org(request)
            member = member_for(request.user, org) if org else None
            if not member or member.role not in roles:
                return HttpResponseForbidden("Your organization role cannot perform this action.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def audit(request, organization, action, entity, obj=None, detail=None):
    if not organization:
        return
    ip = request.META.get("REMOTE_ADDR")
    AuditEvent.objects.create(organization=organization, actor=request.user if request.user.is_authenticated else None,
        action=action, entity_type=entity, entity_id=str(getattr(obj, "pk", "")), detail=detail or {}, ip_address=ip or None)

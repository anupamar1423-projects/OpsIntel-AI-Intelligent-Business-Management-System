from .models import Membership, Notification

def notify_roles(organization, roles, title, body="", url=""):
    recipients=Membership.objects.filter(organization=organization,role__in=roles).values_list("user_id",flat=True).distinct()
    Notification.objects.bulk_create([Notification(organization=organization,recipient_id=user_id,title=title,body=body,url=url) for user_id in recipients])

def notify_user(organization,user,title,body="",url=""):
    if user:
        Notification.objects.create(organization=organization,recipient=user,title=title,body=body,url=url)

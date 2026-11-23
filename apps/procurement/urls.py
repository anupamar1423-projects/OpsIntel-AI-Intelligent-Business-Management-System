from django.urls import path
from .views import listing,review_request,update_order,product_image
urlpatterns=[path("",listing,name="procurement"),path("vendors/<int:vendor_id>/image/",product_image,name="vendor-image"),path("requests/<int:request_id>/review/",review_request,name="review-request"),path("orders/<int:order_id>/update/",update_order,name="update-order")]

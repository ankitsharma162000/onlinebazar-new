from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.seller_register, name='seller_register'),
    path('login/', views.seller_login, name='seller_login'),
    path('logout/', views.seller_logout, name='seller_logout'),
    path('dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('products/', views.seller_products, name='seller_products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<uuid:product_id>/', views.product_edit, name='product_edit'),
    path('products/delete/<uuid:product_id>/', views.product_delete, name='product_delete'),
    path('orders/', views.seller_orders, name='seller_orders'),
    path('orders/update/<uuid:order_id>/', views.update_order_status, name='update_order_status'),
    path('order-requests/', views.seller_order_requests, name='seller_order_requests'),
    path('order-requests/accept/<uuid:req_id>/', views.accept_order_request, name='accept_order_request'),
    path('order-requests/reject/<uuid:req_id>/', views.reject_order_request, name='reject_order_request'),
    path('order-requests/ship/<uuid:req_id>/', views.ship_order_request, name='ship_order_request'),
    path('order-requests/delivered/<uuid:req_id>/', views.mark_delivered, name='mark_delivered'),
    path('profile/', views.seller_profile, name='seller_profile'),
]

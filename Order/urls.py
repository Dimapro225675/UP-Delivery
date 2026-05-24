from django.urls import path
from . import views

app_name = 'Order'

urlpatterns = [
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/history/', views.ClientHistoryView.as_view(), name='client_history'),
    path('orders/dispatcher/', views.DispatcherDashboardView.as_view(), name='dispatcher_dashboard'),
    path('orders/courier/', views.CourierDashboardView.as_view(), name='courier_dashboard'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    path('orders/<int:order_id>/assign/', views.assign_courier, name='assign_courier'),
    path('orders/<int:order_id>/add-status/', views.add_status_history, name='add_status'),
    path('orders/<int:order_id>/confirm/', views.confirm_delivery, name='confirm_delivery'),
    path('scan/', views.scan_tracking, name='scan_tracking'),
    path('tracking/', views.public_tracking, name='public_tracking'),

    path('orders/<int:order_id>/issues/create/', views.IssueCreateView.as_view(), name='issue_create'),
    path('issues/<int:pk>/update/', views.IssueUpdateView.as_view(), name='issue_update'),
]

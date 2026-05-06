from django.urls import path
from . import views

app_name = 'Order'

urlpatterns = [
    path('delivery-types/', views.DeliveryTypeListView.as_view(), name='delivery_type_list'),
    path('delivery-types/<int:pk>/', views.DeliveryTypeDetailView.as_view(), name='delivery_type_detail'),
    path('delivery-types/create/', views.DeliveryTypeCreateView.as_view(), name='delivery_type_create'),
    path('delivery-types/<int:pk>/update/', views.DeliveryTypeUpdateView.as_view(), name='delivery_type_update'),
    path('delivery-types/<int:pk>/delete/', views.DeliveryTypeDeleteView.as_view(), name='delivery_type_delete'),

    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    path('orders/<int:order_id>/add-status/', views.add_status_history, name='add_status'),

    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('orders/<int:order_id>/payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/update/', views.PaymentUpdateView.as_view(), name='payment_update'),

    path('status-history/', views.StatusHistoryListView.as_view(), name='status_history_list'),

    path('issues/', views.IssueListView.as_view(), name='issue_list'),
    path('orders/<int:order_id>/issues/create/', views.IssueCreateView.as_view(), name='issue_create'),
    path('issues/<int:pk>/update/', views.IssueUpdateView.as_view(), name='issue_update'),
]
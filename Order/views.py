from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from .models import Order, Payment, StatusHistory, Issue, DeliveryType
from .forms import (
    DeliveryTypeForm,
    OrderForm,
    PaymentForm,
    IssueForm,
    IssueResolveForm,
)


class DeliveryTypeListView(ListView):
    model = DeliveryType
    template_name = 'delivery/delivery_types_list.html'
    context_object_name = 'delivery_types'


class DeliveryTypeDetailView(DetailView):
    model = DeliveryType
    template_name = 'delivery/delivery_type_detail.html'


class DeliveryTypeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = DeliveryType
    form_class = DeliveryTypeForm
    template_name = 'delivery/delivery_type_form.html'
    success_url = reverse_lazy('Order:delivery_type_list')
    success_message = 'Тип доставки успешно создан'


class DeliveryTypeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DeliveryType
    form_class = DeliveryTypeForm
    template_name = 'delivery/delivery_type_form.html'
    success_url = reverse_lazy('Order:delivery_type_list')
    success_message = 'Тип доставки успешно обновлен'


class DeliveryTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = DeliveryType
    template_name = 'delivery/delivery_type_confirm_delete.html'
    success_url = reverse_lazy('Order:delivery_type_list')


class OrderListView(ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'Order'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        if query:
            queryset = queryset.filter(
                Q(pickup_address__icontains=query) |
                Q(delivery_address__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')


class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['status_history'] = self.object.status_history.all()
        context['issues'] = self.object.issues.all()
        return context


class OrderCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:order_list')
    success_message = 'Заказ успешно создан'

    def form_valid(self, form):
        form.instance.client = self.request.user
        return super().form_valid(form)


class OrderUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('Order:order_list')
    success_message = 'Заказ успешно обновлен'


class OrderDeleteView(LoginRequiredMixin, DeleteView):
    model = Order
    template_name = 'orders/order_confirm_delete.html'
    success_url = reverse_lazy('Order:order_list')


class PaymentListView(ListView):
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20


class PaymentDetailView(DetailView):
    model = Payment
    template_name = 'payments/payment_detail.html'


class PaymentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    success_url = reverse_lazy('Order:payment_list')
    success_message = 'Платеж успешно создан'

    def form_valid(self, form):
        order_id = self.kwargs.get('order_id')
        form.instance.order = get_object_or_404(Order, pk=order_id)
        return super().form_valid(form)


class PaymentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    success_url = reverse_lazy('Order:payment_list')
    success_message = 'Платеж обновлен'


class StatusHistoryListView(ListView):
    model = StatusHistory
    template_name = 'status_history/status_history_list.html'
    context_object_name = 'history'
    paginate_by = 50


def add_status_history(request, order_id):
    if request.method == 'POST' and request.user.is_authenticated:
        order = get_object_or_404(Order, pk=order_id)
        status = request.POST.get('status')
        comment = request.POST.get('comment', '')
        location = request.POST.get('location', '')

        StatusHistory.objects.create(
            order=order,
            status=status,
            courier=request.user,
            comment=comment,
            location=location
        )
        order.status = status
        order.save()

        messages.success(request, 'Статус обновлен')
        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


class IssueListView(ListView):
    model = Issue
    template_name = 'issues/issue_list.html'
    context_object_name = 'issues'
    paginate_by = 20


class IssueCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Issue
    form_class = IssueForm
    template_name = 'issues/issue_form.html'
    success_url = reverse_lazy('Order:issue_list')
    success_message = 'Проблема зарегистрирована'

    def form_valid(self, form):
        order_id = self.kwargs.get('order_id')
        form.instance.order = get_object_or_404(Order, pk=order_id)
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class IssueUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Issue
    form_class = IssueResolveForm
    template_name = 'issues/issue_resolve_form.html'
    success_url = reverse_lazy('Order:issue_list')
    success_message = 'Проблема обновлена'
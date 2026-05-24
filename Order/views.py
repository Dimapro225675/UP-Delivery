from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    DeliveryTypeForm,
    DispatcherAssignCourierForm,
    IssueForm,
    IssueResolveForm,
    OrderForm,
    StatusUpdateForm,
)
from .models import AuditLog, DeliveryType, Issue, Order, StatusHistory


def can_view_order(user, order):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "can_manage_orders", False)
            or order.client_id == user.id
            or order.courier_id == user.id
        )
    )


def can_manage_order(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "can_manage_orders", False))


def is_courier(user):
    return user.is_authenticated and getattr(user, "is_courier", False)


def get_allowed_statuses(user, order):
    if can_manage_order(user):
        return Order.STATUS_FLOW.get(order.status, set())
    if is_courier(user) and order.courier_id == user.id:
        if order.status == Order.STATUS_WAITING_COURIER:
            return {Order.STATUS_DELIVERING}
        if order.status == Order.STATUS_DELIVERING:
            return {Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS}
    return set()


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_order(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DeliveryTypeListView(LoginRequiredMixin, ListView):
    model = DeliveryType
    template_name = "delivery/delivery_types_list.html"
    context_object_name = "delivery_types"


class DeliveryTypeDetailView(LoginRequiredMixin, DetailView):
    model = DeliveryType
    template_name = "delivery/delivery_type_detail.html"


class DeliveryTypeCreateView(StaffRequiredMixin, CreateView):
    model = DeliveryType
    form_class = DeliveryTypeForm
    template_name = "delivery/delivery_type_form.html"
    success_url = reverse_lazy("Order:delivery_type_list")


class DeliveryTypeUpdateView(StaffRequiredMixin, UpdateView):
    model = DeliveryType
    form_class = DeliveryTypeForm
    template_name = "delivery/delivery_type_form.html"
    success_url = reverse_lazy("Order:delivery_type_list")


class DeliveryTypeDeleteView(StaffRequiredMixin, DeleteView):
    model = DeliveryType
    template_name = "delivery/delivery_type_confirm_delete.html"
    success_url = reverse_lazy("Order:delivery_type_list")


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.select_related("client", "courier", "delivery_type")
        user = self.request.user
        if getattr(user, "is_client", False):
            queryset = queryset.filter(client=user).exclude(status=Order.STATUS_CONFIRMED)
        elif getattr(user, "is_courier", False):
            queryset = queryset.filter(courier=user).exclude(status=Order.STATUS_CONFIRMED)
        elif not can_manage_order(user):
            queryset = queryset.none()

        query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        if query:
            queryset = queryset.filter(
                Q(tracking_number__icontains=query)
                | Q(pickup_address__icontains=query)
                | Q(delivery_address__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Order.STATUS_CHOICES
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/order_detail.html"

    def get_queryset(self):
        return Order.objects.select_related("client", "courier", "delivery_type")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_order(request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_history"] = self.object.status_history.select_related("courier")
        context["issues"] = self.object.issues.all()
        context["status_form"] = StatusUpdateForm(
            initial={"status": self.object.status},
            allowed_statuses=get_allowed_statuses(self.request.user, self.object),
        )
        context["can_change_status"] = bool(get_allowed_statuses(self.request.user, self.object))
        context["assign_form"] = DispatcherAssignCourierForm(instance=self.object)
        context["can_manage"] = can_manage_order(self.request.user)
        context["can_confirm"] = self.object.client_id == self.request.user.id and self.object.status in {
            Order.STATUS_DELIVERED_PICKUP_POINT,
            Order.STATUS_DELIVERED_ADDRESS,
        }
        return context


class OrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"
    success_url = reverse_lazy("Order:order_list")

    def form_valid(self, form):
        form.instance.client = self.request.user
        form.instance.status = Order.STATUS_WAITING
        response = super().form_valid(form)
        StatusHistory.objects.create(order=self.object, status=self.object.status, courier=self.request.user, comment="Заказ создан")
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_created", details="Создан новый заказ")
        messages.success(self.request, f"Заказ создан. Трекинг-номер: {self.object.tracking_number}")
        return response


class OrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"
    success_url = reverse_lazy("Order:order_list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_order(request.user, self.object):
            raise PermissionDenied
        if not can_manage_order(request.user) and self.object.status != Order.STATUS_WAITING:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_updated", details="Обновлены данные заказа")
        messages.success(self.request, "Заказ обновлен")
        return response


class OrderDeleteView(LoginRequiredMixin, DeleteView):
    model = Order
    template_name = "orders/order_confirm_delete.html"
    success_url = reverse_lazy("Order:order_list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_order(request.user, self.object):
            raise PermissionDenied
        if not can_manage_order(request.user) and self.object.status != Order.STATUS_WAITING:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.status = Order.STATUS_CANCELLED
        self.object.save()
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_cancelled", details="Заказ отменен")
        messages.success(self.request, "Заказ отменен")
        return redirect(self.success_url)


class DispatcherDashboardView(StaffRequiredMixin, ListView):
    model = Order
    template_name = "orders/dispatcher_dashboard.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.select_related("client", "courier", "delivery_type").filter(
            status__in=[Order.STATUS_WAITING, Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING]
        )


class CourierDashboardView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/courier_dashboard.html"
    context_object_name = "orders"

    def dispatch(self, request, *args, **kwargs):
        if not is_courier(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Order.objects.select_related("client", "delivery_type").filter(
            courier=self.request.user,
            status__in=[Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING],
        )


def assign_courier(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not can_manage_order(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = DispatcherAssignCourierForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            if order.status == Order.STATUS_WAITING:
                order.status = Order.STATUS_WAITING_COURIER
            order.save()
            StatusHistory.objects.create(
                order=order,
                status=order.status,
                courier=request.user,
                comment=f"Назначен курьер: {order.courier}",
            )
            AuditLog.objects.create(
                user=request.user,
                order=order,
                action="courier_assigned",
                details=f"Курьер: {order.courier}",
            )
            messages.success(request, "Курьер назначен")
    return redirect("Order:order_detail", pk=order.pk)


def add_status_history(request, order_id):
    if request.method != "POST" or not request.user.is_authenticated:
        return redirect("Order:order_detail", pk=order_id)
    order = get_object_or_404(Order, pk=order_id)
    if not can_view_order(request.user, order):
        raise PermissionDenied

    form = StatusUpdateForm(request.POST, request.FILES, allowed_statuses=get_allowed_statuses(request.user, order))
    if form.is_valid():
        try:
            if form.cleaned_data["status"] == Order.STATUS_DELIVERED_ADDRESS and not (
                form.cleaned_data.get("delivery_report_photo") or order.delivery_report_photo
            ):
                raise ValidationError("Для доставки по адресу нужно загрузить фотоотчет")
            if form.cleaned_data.get("delivery_report_photo"):
                order.delivery_report_photo = form.cleaned_data["delivery_report_photo"]
            order.set_status(
                form.cleaned_data["status"],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )
            messages.success(request, "Статус обновлен")
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
    return redirect("Order:order_detail", pk=order.pk)


def confirm_delivery(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not request.user.is_authenticated or order.client_id != request.user.id:
        raise PermissionDenied
    if request.method == "POST" and order.status in {Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS}:
        order.set_status(Order.STATUS_CONFIRMED, user=request.user, comment="Клиент подтвердил доставку")
        messages.success(request, "Доставка подтверждена. Заказ перенесен в историю.")
    return redirect("Order:order_detail", pk=order.pk)


def public_tracking(request):
    order = None
    history = []
    query = request.GET.get("tracking_number", "").strip()
    if query:
        order = get_object_or_404(Order.objects.select_related("client", "courier", "delivery_type"), tracking_number=query)
        history = order.status_history.select_related("courier")
    return render(request, "orders/public_tracking.html", {"order": order, "history": history, "query": query})


class ClientHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/client_history.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.select_related("delivery_type", "courier").prefetch_related("issues").filter(
            client=self.request.user,
        )


def scan_tracking(request):
    if not is_courier(request.user) and not can_manage_order(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = StatusUpdateForm(request.POST, request.FILES)
        tracking_number = request.POST.get("tracking_number")
        order = get_object_or_404(Order, tracking_number=tracking_number)
        if not can_view_order(request.user, order):
            raise PermissionDenied
        if form.is_valid():
            if form.cleaned_data["status"] == Order.STATUS_DELIVERED_ADDRESS and not (
                form.cleaned_data.get("delivery_report_photo") or order.delivery_report_photo
            ):
                messages.error(request, "Для доставки по адресу нужно загрузить фотоотчет")
                return redirect("Order:order_detail", pk=order.pk)
            if form.cleaned_data.get("delivery_report_photo"):
                order.delivery_report_photo = form.cleaned_data["delivery_report_photo"]
            try:
                order.set_status(
                    form.cleaned_data["status"],
                    user=request.user,
                    comment=form.cleaned_data["comment"],
                )
                messages.success(request, "Статус по трекинг-номеру обновлен")
                return redirect("Order:order_detail", pk=order.pk)
            except ValidationError as error:
                messages.error(request, "; ".join(error.messages))
    else:
        form = StatusUpdateForm()
    return render(request, "orders/scan_tracking.html", {"form": form})


class IssueCreateView(StaffRequiredMixin, CreateView):
    model = Issue
    form_class = IssueForm
    template_name = "issues/issue_form.html"

    def form_valid(self, form):
        order = get_object_or_404(Order, pk=self.kwargs.get("order_id"))
        form.instance.order = order
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        order.delivery_attempts += 1
        if order.delivery_attempts >= order.max_delivery_attempts and order.status == Order.STATUS_DELIVERING:
            order.set_status(Order.STATUS_RETURNED, user=self.request.user, comment="Превышено число попыток вручения")
        else:
            order.save()
        AuditLog.objects.create(user=self.request.user, order=order, action="issue_created", details=form.instance.description)
        messages.success(self.request, "Исключительная ситуация зарегистрирована")
        return response

    def get_success_url(self):
        return reverse_lazy("Order:order_detail", kwargs={"pk": self.object.order_id})


class IssueUpdateView(StaffRequiredMixin, UpdateView):
    model = Issue
    form_class = IssueResolveForm
    template_name = "issues/issue_resolve_form.html"

    def get_success_url(self):
        return reverse_lazy("Order:order_detail", kwargs={"pk": self.object.order_id})


def home(request):
    orders = Order.objects.all()
    if request.user.is_authenticated:
        if getattr(request.user, "is_client", False):
            orders = orders.filter(client=request.user)
        elif getattr(request.user, "is_courier", False):
            orders = orders.filter(courier=request.user)
    total_orders = orders.count()
    active_orders = orders.filter(status__in=[Order.STATUS_WAITING, Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING]).count()
    delivered_orders = orders.filter(status__in=[Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS, Order.STATUS_CONFIRMED]).count()
    issues_count = Issue.objects.filter(resolved=False).count()
    latest_orders = orders.select_related("client", "delivery_type").order_by("-created_at")[:5]
    return render(
        request,
        "home.html",
        {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "delivered_orders": delivered_orders,
            "issues_count": issues_count,
            "latest_orders": latest_orders,
        },
    )

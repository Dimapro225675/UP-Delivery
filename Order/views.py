from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
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
from .models import AuditLog, DeliveryReportPhoto, DeliveryType, Issue, Order, OrderHistoryHiddenEntry, OrderPhoto, StatusHistory


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


def can_cancel_order(user, order):
    return user.is_authenticated and (
        order.client_id == user.id
        or user.is_superuser
        or getattr(user, "is_dispatcher", False)
        or getattr(user, "is_business_admin", False)
    )


def is_courier(user):
    return user.is_authenticated and getattr(user, "is_courier", False)


def can_reassign_courier(user, order):
    return can_manage_order(user) and order.status in {
        Order.STATUS_WAITING,
        Order.STATUS_WAITING_COURIER,
        Order.STATUS_DELIVERING,
    }


def can_refuse_order(user, order):
    return (
        is_courier(user)
        and order.courier_id == user.id
        and order.status in {Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING}
    )


def can_hide_order_from_history(user, order):
    terminal_statuses = {
        Order.STATUS_DELIVERED_PICKUP_POINT,
        Order.STATUS_DELIVERED_ADDRESS,
        Order.STATUS_CONFIRMED,
        Order.STATUS_RETURNED,
        Order.STATUS_CANCELLED,
    }
    return (
        user.is_authenticated
        and order.status in terminal_statuses
        and (user.is_superuser or order.client_id == user.id)
    )


def can_report_issue(user, order):
    return user.is_authenticated and (
        can_manage_order(user)
        or (is_courier(user) and order.courier_id == user.id)
    )


def can_delete_issue(user, issue):
    return (
        issue.resolved
        and user.is_authenticated
        and (
            can_manage_order(user)
            or (is_courier(user) and issue.order.courier_id == user.id)
        )
    )


def can_view_all_client_pages(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "can_view_all_client_pages", False))


def get_allowed_statuses(user, order):
    if can_manage_order(user):
        return Order.STATUS_FLOW.get(order.status, set())
    if is_courier(user) and order.courier_id == user.id:
        if order.status == Order.STATUS_WAITING_COURIER:
            return {Order.STATUS_DELIVERING}
        if order.status == Order.STATUS_DELIVERING:
            return {Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS}
    return set()


def create_order_photos(order, files):
    OrderPhoto.objects.bulk_create([OrderPhoto(order=order, image=file) for file in files])


def create_delivery_report_photos(order, files):
    DeliveryReportPhoto.objects.bulk_create([DeliveryReportPhoto(order=order, image=file) for file in files])


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
        queryset = Order.objects.select_related("client", "courier", "delivery_type").prefetch_related("order_photos")
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


class OrderListRedirectView(LoginRequiredMixin, ListView):
    def get(self, request, *args, **kwargs):
        if can_view_all_client_pages(request.user) or can_manage_order(request.user):
            return HttpResponseRedirect(reverse_lazy("Order:dispatcher_dashboard"))
        if is_courier(request.user):
            return HttpResponseRedirect(reverse_lazy("Order:courier_dashboard"))
        return HttpResponseRedirect(reverse_lazy("Order:client_history"))


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/order_detail.html"

    def get_queryset(self):
        return (
            Order.objects.select_related("client", "courier", "delivery_type")
            .prefetch_related("order_photos", "delivery_report_photos", "issues", "status_history")
        )

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
        context["can_reassign_courier"] = can_reassign_courier(self.request.user, self.object)
        context["can_refuse_order"] = can_refuse_order(self.request.user, self.object)
        context["can_cancel"] = can_cancel_order(self.request.user, self.object) and self.object.status != Order.STATUS_CANCELLED
        context["can_report_issue"] = can_report_issue(self.request.user, self.object)
        context["can_confirm"] = self.object.client_id == self.request.user.id and self.object.status in {
            Order.STATUS_DELIVERED_PICKUP_POINT,
            Order.STATUS_DELIVERED_ADDRESS,
        }
        return context


class OrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["delivery_type_data"] = list(
            DeliveryType.objects.order_by("name").values("id", "name", "base_price", "max_distance")
        )
        context["delivery_pricing"] = {
            "included_weight_kg": float(Order.INCLUDED_WEIGHT_KG),
            "included_side_cm": float(Order.INCLUDED_SIDE_CM),
            "address_delivery_surcharge": float(Order.ADDRESS_DELIVERY_SURCHARGE),
            "overweight_price_per_kg": float(Order.OVERWEIGHT_PRICE_PER_KG),
            "oversize_price_per_10_cm": float(Order.OVERSIZE_PRICE_PER_10_CM),
            "intercity_price_per_10_km": float(Order.INTERCITY_PRICE_PER_10_KM),
            "city_distances_km": {",".join(sorted(key)): value for key, value in Order.CITY_DISTANCES_KM.items()},
        }
        return context

    def form_valid(self, form):
        files = self.request.FILES.getlist("order_photos")
        if not files:
            form.add_error("order_photos", "Добавьте хотя бы одну фотографию заказа")
            return self.form_invalid(form)
        form.instance.client = self.request.user
        form.instance.status = Order.STATUS_WAITING
        response = super().form_valid(form)
        create_order_photos(self.object, files)
        StatusHistory.objects.create(order=self.object, status=self.object.status, courier=self.request.user, comment="Заказ создан")
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_created", details="Создан новый заказ")
        messages.success(self.request, f"Заказ создан. Трекинг-номер: {self.object.tracking_number}")
        return response

    def get_success_url(self):
        return reverse_lazy("Order:order_detail", kwargs={"pk": self.object.pk})


class OrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["delivery_type_data"] = list(
            DeliveryType.objects.order_by("name").values("id", "name", "base_price", "max_distance")
        )
        context["delivery_pricing"] = {
            "included_weight_kg": float(Order.INCLUDED_WEIGHT_KG),
            "included_side_cm": float(Order.INCLUDED_SIDE_CM),
            "address_delivery_surcharge": float(Order.ADDRESS_DELIVERY_SURCHARGE),
            "overweight_price_per_kg": float(Order.OVERWEIGHT_PRICE_PER_KG),
            "oversize_price_per_10_cm": float(Order.OVERSIZE_PRICE_PER_10_CM),
            "intercity_price_per_10_km": float(Order.INTERCITY_PRICE_PER_10_KM),
            "city_distances_km": {",".join(sorted(key)): value for key, value in Order.CITY_DISTANCES_KM.items()},
        }
        return context

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_order(request.user, self.object):
            raise PermissionDenied
        if request.user.id != self.object.client_id and not can_manage_order(request.user):
            raise PermissionDenied
        if request.user.id == self.object.client_id and not can_manage_order(request.user) and self.object.status != Order.STATUS_WAITING:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        files = self.request.FILES.getlist("order_photos")
        if not files and not self.object.order_photos.exists():
            form.add_error("order_photos", "Добавьте хотя бы одну фотографию заказа")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if files:
            create_order_photos(self.object, files)
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_updated", details="Обновлены данные заказа")
        messages.success(self.request, "Заказ обновлен")
        return response

    def get_success_url(self):
        return reverse_lazy("Order:order_detail", kwargs={"pk": self.object.pk})


class OrderDeleteView(LoginRequiredMixin, DeleteView):
    model = Order
    template_name = "orders/order_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_order(request.user, self.object):
            raise PermissionDenied
        if self.object.status == Order.STATUS_CANCELLED or not can_cancel_order(request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.cancel(user=self.request.user)
        AuditLog.objects.create(user=self.request.user, order=self.object, action="order_cancelled", details="Заказ отменен")
        messages.success(self.request, "Заказ отменен")
        return redirect(self.get_success_url())

    def get_success_url(self):
        if can_view_all_client_pages(self.request.user) or can_manage_order(self.request.user):
            return reverse_lazy("Order:dispatcher_dashboard")
        return reverse_lazy("Order:client_history")


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
        if not is_courier(request.user) and not can_view_all_client_pages(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Order.objects.select_related("client", "delivery_type", "courier").filter(
            status__in=[Order.STATUS_WAITING_COURIER, Order.STATUS_DELIVERING],
        )
        if can_view_all_client_pages(self.request.user):
            return queryset
        return queryset.filter(courier=self.request.user)


def assign_courier(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not can_reassign_courier(request.user, order):
        raise PermissionDenied
    if request.method == "POST":
        previous_courier = order.courier
        previous_courier_id = order.courier_id
        form = DispatcherAssignCourierForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            if previous_courier_id and previous_courier_id == order.courier_id:
                messages.info(request, "Курьер уже назначен на этот заказ")
                return redirect("Order:order_detail", pk=order.pk)
            order.status = Order.STATUS_WAITING_COURIER
            order.save()
            comment = (
                f"Курьер изменен: {previous_courier} -> {order.courier}"
                if previous_courier
                else f"Назначен курьер: {order.courier}"
            )
            StatusHistory.objects.create(
                order=order,
                status=order.status,
                courier=request.user,
                comment=comment,
            )
            AuditLog.objects.create(
                user=request.user,
                order=order,
                action="courier_reassigned" if previous_courier else "courier_assigned",
                details=comment,
            )
            messages.success(request, "Курьер изменен" if previous_courier else "Курьер назначен")
    return redirect("Order:order_detail", pk=order.pk)


def refuse_order(request, order_id):
    if request.method != "POST":
        return redirect("Order:order_detail", pk=order_id)
    order = get_object_or_404(Order, pk=order_id)
    if not can_refuse_order(request.user, order):
        raise PermissionDenied

    refused_courier = order.courier
    order.courier = None
    order.status = Order.STATUS_WAITING
    order.save()
    comment = f"Курьер отказался от заказа: {refused_courier}"
    StatusHistory.objects.create(
        order=order,
        status=order.status,
        courier=request.user,
        comment=comment,
    )
    AuditLog.objects.create(
        user=request.user,
        order=order,
        action="courier_refused",
        details=comment,
    )
    messages.success(request, "Вы отказались от заказа. Он возвращен диспетчеру на переназначение.")
    return redirect("Order:courier_dashboard")


def add_status_history(request, order_id):
    if request.method != "POST" or not request.user.is_authenticated:
        return redirect("Order:order_detail", pk=order_id)
    order = get_object_or_404(Order, pk=order_id)
    if not can_view_order(request.user, order):
        raise PermissionDenied

    form = StatusUpdateForm(request.POST, request.FILES, allowed_statuses=get_allowed_statuses(request.user, order))
    if form.is_valid():
        files = request.FILES.getlist("delivery_report_photos")
        try:
            if form.cleaned_data["status"] == Order.STATUS_DELIVERED_ADDRESS and not (files or order.delivery_report_photos.exists()):
                raise ValidationError("Для доставки по адресу нужно загрузить фотоотчет")
            order.set_status(
                form.cleaned_data["status"],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )
            if files:
                create_delivery_report_photos(order, files)
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
        order = get_object_or_404(
            Order.objects.select_related("client", "courier", "delivery_type").prefetch_related("delivery_report_photos", "order_photos"),
            tracking_number=query,
        )
        history = order.status_history.select_related("courier")
    return render(request, "orders/public_tracking.html", {"order": order, "history": history, "query": query})


class ClientHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "orders/client_history.html"
    context_object_name = "orders"

    def get_queryset(self):
        queryset = (
            Order.objects.select_related("delivery_type", "courier", "client")
            .prefetch_related("issues")
            .exclude(hidden_in_history_entries__user=self.request.user)
        )
        if self.request.user.is_superuser:
            return queryset.order_by("-created_at")
        if can_manage_order(self.request.user):
            return queryset.filter(client=self.request.user).order_by("-created_at")
        if is_courier(self.request.user):
            return queryset.filter(client=self.request.user).order_by("-created_at")
        return queryset.filter(client=self.request.user).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_superuser:
            context["cabinet_title"] = "Личный кабинет"
            context["cabinet_subtitle"] = "Профиль пользователя и все доступные заказы в системе."
        elif can_view_all_client_pages(user):
            context["cabinet_title"] = "Личный кабинет"
            context["cabinet_subtitle"] = "Профиль пользователя и все доступные заказы в системе."
        elif can_manage_order(user):
            context["cabinet_title"] = "Личный кабинет"
            context["cabinet_subtitle"] = "Профиль диспетчера и заказы, созданные вами."
        elif is_courier(user):
            context["cabinet_title"] = "Личный кабинет"
            context["cabinet_subtitle"] = "Профиль курьера и заказы, закрепленные за вами."
        else:
            context["cabinet_title"] = "Личный кабинет"
            context["cabinet_subtitle"] = "Ваш профиль, статусы, маршруты и стоимость заказов."
        return context
def hide_order_from_history(request, order_id):
    if request.method != "POST" or not request.user.is_authenticated:
        return redirect("Order:client_history")
    order = get_object_or_404(Order, pk=order_id)
    if not can_hide_order_from_history(request.user, order):
        raise PermissionDenied

    OrderHistoryHiddenEntry.objects.get_or_create(user=request.user, order=order)
    messages.success(request, "Заказ скрыт из вашей истории.")
    return redirect("Order:client_history")


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
            files = request.FILES.getlist("delivery_report_photos")
            if form.cleaned_data["status"] == Order.STATUS_DELIVERED_ADDRESS and not (files or order.delivery_report_photos.exists()):
                messages.error(request, "Для доставки по адресу нужно загрузить фотоотчет")
                return redirect("Order:order_detail", pk=order.pk)
            try:
                order.set_status(
                    form.cleaned_data["status"],
                    user=request.user,
                    comment=form.cleaned_data["comment"],
                )
                if files:
                    create_delivery_report_photos(order, files)
                messages.success(request, "Статус по трекинг-номеру обновлен")
                return redirect("Order:order_detail", pk=order.pk)
            except ValidationError as error:
                messages.error(request, "; ".join(error.messages))
    else:
        form = StatusUpdateForm()
    return render(request, "orders/scan_tracking.html", {"form": form})


class IssueCreateView(LoginRequiredMixin, CreateView):
    model = Issue
    form_class = IssueForm
    template_name = "issues/issue_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, pk=self.kwargs.get("order_id"))
        if not can_report_issue(request.user, self.order):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.order = self.order
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        AuditLog.objects.create(user=self.request.user, order=self.order, action="issue_created", details=form.instance.description)
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


class IssueDeleteView(LoginRequiredMixin, DeleteView):
    model = Issue
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_delete_issue(request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        order = self.object.order
        description = self.object.description
        self.object.delete()
        AuditLog.objects.create(
            user=self.request.user,
            order=order,
            action="issue_deleted",
            details=description,
        )
        messages.success(self.request, "Проблемная ситуация удалена")
        return redirect(self.get_success_url())

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
    delivered_orders = orders.filter(
        status__in=[Order.STATUS_DELIVERED_PICKUP_POINT, Order.STATUS_DELIVERED_ADDRESS, Order.STATUS_CONFIRMED]
    ).count()
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

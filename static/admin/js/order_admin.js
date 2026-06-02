(function () {
  function parseJsonAttr(element, attrName) {
    if (!element) {
      return null;
    }
    const value = element.getAttribute(attrName);
    if (!value) {
      return null;
    }
    try {
      return JSON.parse(value);
    } catch (error) {
      return null;
    }
  }

  function parseNumber(element) {
    if (!element) {
      return null;
    }
    const value = parseFloat(element.value || "");
    return Number.isFinite(value) ? value : null;
  }

  function roundUp(value) {
    return Math.ceil(value);
  }

  function updateAdminOrderSummary() {
    const pickupCity = document.getElementById("id_pickup_city");
    const deliveryCity = document.getElementById("id_delivery_city");
    const deliveryType = document.getElementById("id_delivery_type");
    const pickupPoint = document.getElementById("id_delivery_to_pickup_point");
    const weight = document.getElementById("id_weight_kg");
    const length = document.getElementById("id_length_cm");
    const width = document.getElementById("id_width_cm");
    const height = document.getElementById("id_height_cm");
    const distanceField = document.getElementById("id_distance_km");
    const priceField = document.getElementById("id_delivery_price");

    if (!pickupCity || !deliveryCity || !deliveryType || !distanceField || !priceField) {
      return;
    }

    const cityDistances = parseJsonAttr(pickupCity, "data-city-distances") || {};
    const deliveryTypes = parseJsonAttr(deliveryType, "data-delivery-types") || [];
    const pricingConfig = parseJsonAttr(priceField, "data-pricing-config") || {};

    const deliveryTypeRow = deliveryType.closest(".form-row, .field-delivery_type, .form-group");
    let hint = document.getElementById("admin-delivery-type-hint");
    if (!hint && deliveryTypeRow) {
      hint = document.createElement("div");
      hint.id = "admin-delivery-type-hint";
      hint.style.marginTop = "8px";
      hint.style.padding = "10px 12px";
      hint.style.border = "1px solid #d7e3d1";
      hint.style.borderRadius = "10px";
      hint.style.background = "#f7faf4";
      hint.style.fontSize = "13px";
      hint.style.lineHeight = "1.5";
      deliveryTypeRow.appendChild(hint);
    }

    const getDistance = function () {
      if (!pickupCity.value || !deliveryCity.value) {
        return null;
      }
      if (pickupCity.value === deliveryCity.value) {
        return 0;
      }
      const key = [pickupCity.value, deliveryCity.value].sort().join(",");
      return cityDistances[key] ?? 100;
    };

    const distance = getDistance();
    distanceField.value = distance === null ? "" : String(distance);

    const selectedType = deliveryTypes.find((item) => String(item.id) === String(deliveryType.value || ""));
    if (hint) {
      if (selectedType) {
        const maxDistanceText = `${selectedType.max_distance} км`;
        const basePriceText = `${Number(selectedType.base_price).toFixed(2)} ₽`;
        hint.innerHTML = `<strong>Тип доставки:</strong> базовая цена ${basePriceText}, максимум ${maxDistanceText}.`;
      } else {
        hint.innerHTML = "Выберите тип доставки, чтобы увидеть базовую цену и максимальное расстояние.";
      }
    }

    const currentWeight = parseNumber(weight);
    const currentLength = parseNumber(length);
    const currentWidth = parseNumber(width);
    const currentHeight = parseNumber(height);

    if (!selectedType || currentWeight === null || currentLength === null || currentWidth === null || currentHeight === null) {
      priceField.value = "";
      return;
    }

    let total = parseFloat(selectedType.base_price);
    if (!pickupPoint || !pickupPoint.checked) {
      total += pricingConfig.address_delivery_surcharge || 0;
    }

    if (currentWeight > (pricingConfig.included_weight_kg || 0)) {
      total += (currentWeight - pricingConfig.included_weight_kg) * (pricingConfig.overweight_price_per_kg || 0);
    }

    [currentLength, currentWidth, currentHeight].forEach((side) => {
      if (side > (pricingConfig.included_side_cm || 0)) {
        total += roundUp((side - pricingConfig.included_side_cm) / 10) * (pricingConfig.oversize_price_per_10_cm || 0);
      }
    });

    if (distance && distance > 0) {
      total += roundUp(distance / 10) * (pricingConfig.intercity_price_per_10_km || 0);
    }

    priceField.value = total.toFixed(2);
  }

  function boot() {
    const fieldIds = [
      "id_pickup_city",
      "id_delivery_city",
      "id_delivery_type",
      "id_delivery_to_pickup_point",
      "id_weight_kg",
      "id_length_cm",
      "id_width_cm",
      "id_height_cm",
    ];

    fieldIds.forEach((fieldId) => {
      const field = document.getElementById(fieldId);
      if (!field) {
        return;
      }
      field.addEventListener("change", updateAdminOrderSummary);
      field.addEventListener("input", updateAdminOrderSummary);
    });

    document.addEventListener("change", function (event) {
      if (fieldIds.includes(event.target.id)) {
        updateAdminOrderSummary();
      }
    });

    document.addEventListener("input", function (event) {
      if (fieldIds.includes(event.target.id)) {
        updateAdminOrderSummary();
      }
    });

    window.setTimeout(updateAdminOrderSummary, 0);
    window.setTimeout(updateAdminOrderSummary, 150);
    updateAdminOrderSummary();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  window.addEventListener("load", updateAdminOrderSummary);
})();

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from pywebpush import WebPushException, webpush

from .models import PushSubscription

logger = logging.getLogger(__name__)


@login_required
def home(request):
    return render(
        request,
        "pushdemo/home.html",
        {
            "vapid_public_key": settings.VAPID_PUBLIC_KEY,
            "subscription_count": PushSubscription.objects.filter(user=request.user).count(),
        },
    )


@login_required
@require_POST
def subscribe(request):
    try:
        data = json.loads(request.body or "{}")
        endpoint = data["endpoint"]
        keys = data["keys"]
        p256dh = keys["p256dh"]
        auth = keys["auth"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "Некорректная push-подписка."}, status=400)

    if not all(isinstance(value, str) and value for value in (endpoint, p256dh, auth)):
        return JsonResponse({"ok": False, "error": "В подписке отсутствуют обязательные поля."}, status=400)

    subscription, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"ok": True, "id": subscription.pk, "count": PushSubscription.objects.filter(user=request.user).count()})


@login_required
@require_POST
def unsubscribe(request):
    try:
        data = json.loads(request.body or "{}")
        endpoint = data["endpoint"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "Некорректный запрос."}, status=400)

    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({"ok": True, "count": PushSubscription.objects.filter(user=request.user).count()})


@login_required
@require_POST
def send_test(request):
    try:
        return _send_test_impl(request)
    except Exception:
        logger.exception("Unexpected error in send_test")
        return JsonResponse(
            {"ok": False, "error": "Внутренняя ошибка сервера. Подробности записаны в журнал."},
            status=500,
        )


def _send_test_impl(request):
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        return JsonResponse(
            {
                "ok": False,
                "error": "На сервере не настроены VAPID_PUBLIC_KEY и VAPID_PRIVATE_KEY.",
            },
            status=503,
        )

    try:
        data = json.loads(request.body or "{}")
    except (ValueError, TypeError):
        return JsonResponse(
            {"ok": False, "error": "Некорректный JSON."},
            status=400,
        )

    title = str(data.get("title", "Тестовое уведомление")).strip()[:100]
    body = str(data.get("body", "Push-уведомления работают!")).strip()[:500]

    if not title or not body:
        return JsonResponse(
            {"ok": False, "error": "Укажи заголовок и текст."},
            status=400,
        )

    subscriptions = list(
        PushSubscription.objects.filter(user=request.user)
    )

    if not subscriptions:
        return JsonResponse(
            {
                "ok": False,
                "error": "Сначала включи уведомления на этом устройстве.",
            },
            status=400,
        )

    sent = 0
    expired_ids = []
    errors = []

    payload = json.dumps(
        {"title": title, "body": body, "url": "/"},
        ensure_ascii=False,
    )

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=60 * 60,
            )
            sent += 1

        except WebPushException as exc:
            status_code = getattr(
                getattr(exc, "response", None),
                "status_code",
                None,
            )
            logger.warning("Web Push failed (HTTP %s)", status_code)

            if status_code in (404, 410):
                expired_ids.append(subscription.pk)
            else:
                errors.append(
                    f"Ошибка push-сервиса (HTTP {status_code or 'неизвестно'})."
                )

    if expired_ids:
        PushSubscription.objects.filter(pk__in=expired_ids).delete()

    if sent:
        return JsonResponse(
            {"ok": True, "sent": sent, "errors": errors}
        )

    return JsonResponse(
        {
            "ok": False,
            "error": errors[0]
            if errors
            else "Не удалось отправить push. Проверьте разрешения и VAPID.",
        },
        status=502,
    )


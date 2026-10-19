(() => {
  const config = window.PUSH_DEMO;
  const result = document.querySelector("#result");
  const subscribeButton = document.querySelector("#subscribe-button");
  const unsubscribeButton = document.querySelector("#unsubscribe-button");
  const form = document.querySelector("#push-form");
  const count = document.querySelector("#subscription-count");

  function showResult(message, kind = "success") {
    result.hidden = false;
    result.className = `notice ${kind}`;
    result.textContent = message;
  }

  function csrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input) return input.value;
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Ошибка запроса (${response.status}).`);
    }
    return data;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = window.atob(base64);
    return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
  }

  async function getRegistration() {
    if (!("serviceWorker" in navigator)) {
      throw new Error("Этот браузер не поддерживает service worker.");
    }
    return navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
  }

  async function updateCount() {
    // Count is refreshed on page load; a reload reflects server-side changes.
  }

  subscribeButton.addEventListener("click", async () => {
    subscribeButton.disabled = true;
    try {
      if (!window.isSecureContext) {
        throw new Error("Push требует HTTPS (или localhost для локальной разработки).");
      }
      if (!("PushManager" in window) || !("Notification" in window)) {
        throw new Error("Этот браузер не поддерживает Web Push.");
      }
      if (!config.publicKey) {
        throw new Error("На сервере не задан VAPID_PUBLIC_KEY.");
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        throw new Error("Разрешение на уведомления не предоставлено.");
      }

      const registration = await getRegistration();
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(config.publicKey)
        });
      }
      const saved = await postJSON(config.subscribeUrl, subscription.toJSON());
      showResult("Готово: устройство подписано на push-уведомления.");
      count.textContent = String(saved.count);
    } catch (error) {
      showResult(error.message || "Не удалось подписать устройство.", "error");
    } finally {
      subscribeButton.disabled = false;
    }
  });

  unsubscribeButton.addEventListener("click", async () => {
    unsubscribeButton.disabled = true;
    try {
      const registration = await getRegistration();
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        showResult("На этом устройстве нет активной подписки.", "error");
        return;
      }
      const removed = await postJSON(config.unsubscribeUrl, { endpoint: subscription.endpoint });
      await subscription.unsubscribe();
      count.textContent = String(removed.count);
      showResult("Подписка этого устройства отключена.");
    } catch (error) {
      showResult(error.message || "Не удалось отключить подписку.", "error");
    } finally {
      unsubscribeButton.disabled = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = form.querySelector('[type="submit"]');
    submitButton.disabled = true;
    try {
      const data = await postJSON(config.sendUrl, {
        title: document.querySelector("#push-title").value,
        body: document.querySelector("#push-body").value
      });
      const suffix = data.errors?.length ? ` Предупреждения: ${data.errors.join(" ")}` : "";
      showResult(`Push отправлен: ${data.sent} устройство(а).${suffix}`);
    } catch (error) {
      showResult(error.message || "Не удалось отправить уведомление.", "error");
    } finally {
      submitButton.disabled = false;
    }
  });

  getRegistration().catch((error) => {
    console.error("Service worker registration failed:", error);
  });
})();

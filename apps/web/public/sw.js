self.addEventListener("push", (event) => {
  const payload = event.data?.json() ?? {
    title: "클래식허블",
    body: "관심곡 공연이 새로 감지되었습니다.",
  };

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      data: payload.url ? { url: payload.url } : undefined,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url ?? "/";
  event.waitUntil(self.clients.openWindow(url));
});

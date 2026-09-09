chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.action !== 'WRITE_CONTEXT_FILE') return;
  if (!self.CareerOsDirStore) {
    sendResponse({ ok: false, error: 'dir-store missing' });
    return;
  }
  CareerOsDirStore.writeContext(msg.context).then((info) => {
    sendResponse({ ok: true, folder: info.folder, name: info.name, path: info.folder + '/' + info.name });
  }).catch((err) => {
    sendResponse({ ok: false, error: (err && err.code) || String(err && err.message ? err.message : err) });
  });
  return true;
});

/**
 * 画像只在扩展进程内读取，不通过 web_accessible_resources 暴露给网页。
 * 填表指令广播到当前标签全部 iframe（北森表单常在子帧）。
 */

try { importScripts('runtime-log.js'); } catch (_) { /* ignore */ }

const CONTENT_JS = ['field-map.js', 'runtime-log.js', 'beisen-fill.js', 'content.js'];
const CONTENT_CSS = ['content.css'];

function mergeCaptures(results) {
  const frames = (results || []).filter((r) => r && r.ok && r.context);
  if (!frames.length) return null;
  const top = frames.find((f) => f.context.frame === 'top') || frames[0];
  const ctx = Object.assign({}, top.context);
  let bestJd = ctx.jd_text || '';
  ctx.form_schema = [];
  frames.forEach((f) => {
    const c = f.context;
    if ((c.jd_text || '').length > bestJd.length) {
      bestJd = c.jd_text;
      if (c.title) ctx.title = c.title;
      if (c.company) ctx.company = c.company;
    }
    ctx.form_schema = ctx.form_schema.concat(c.form_schema || []);
  });
  ctx.jd_text = bestJd;
  delete ctx.frame;
  return ctx;
}

function waitDownloadPath(downloadId, timeoutMs) {
  const started = Date.now();
  return new Promise((resolve) => {
    function poll() {
      chrome.downloads.search({ id: downloadId }, (items) => {
        const item = items && items[0];
        if (item && item.filename && (item.state === 'complete' || item.exists !== false)) {
          resolve(item.filename);
          return;
        }
        if (Date.now() - started > timeoutMs) {
          resolve((item && item.filename) || '');
          return;
        }
        setTimeout(poll, 80);
      });
    }
    poll();
  });
}

const RECEIVER_URL = 'http://127.0.0.1:18765';

function downloadContext(ctx) {
  const text = JSON.stringify(ctx, null, 2);
  const dataUrl = 'data:application/json;charset=utf-8,' + encodeURIComponent(text);
  const host = (ctx.host || 'job').replace(/[^a-zA-Z0-9.-]/g, '_');
  const stamp = String(ctx.captured_at || new Date().toISOString())
    .replace(/[:.]/g, '-')
    .replace(/Z$/, '')
    .slice(0, 19);
  const filename = 'career-os-captures/job-context-' + host + '-' + stamp + '.json';
  return chrome.downloads.download({
    url: dataUrl,
    filename: filename,
    saveAs: false,
    conflictAction: 'uniquify'
  }).then((id) => {
    if (!id) return { text: text, path: filename };
    return waitDownloadPath(id, 2500).then((path) => ({ text: text, path: path || filename }));
  }).catch(() => ({ text: text, path: filename }));
}

async function saveToReceiver(ctx) {
  const text = JSON.stringify(ctx, null, 2);
  const res = await fetch(RECEIVER_URL + '/job-context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: text
  });
  if (!res.ok) throw new Error('receiver HTTP ' + res.status);
  const data = await res.json();
  if (!data || !data.ok) throw new Error((data && data.error) || 'receiver failed');
  return { text: text, path: data.path, via: 'project' };
}

async function ensureOffscreen() {
  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['BLOBS'],
      justification: 'Write JobContext JSON into the bound Career OS project folder'
    });
  } catch (err) {
    const msg = String(err && err.message ? err.message : err);
    if (!/already|Only a single/i.test(msg)) throw err;
  }
}

async function saveToBoundFolder(ctx) {
  const text = JSON.stringify(ctx, null, 2);
  await ensureOffscreen();
  const reply = await chrome.runtime.sendMessage({ action: 'WRITE_CONTEXT_FILE', context: ctx });
  if (!reply || !reply.ok) throw new Error((reply && reply.error) || 'NO_DIR');
  return { text: text, path: reply.path, via: 'folder' };
}

function sendNative(payload) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const port = chrome.runtime.connectNative('com.careeros.jobcontext');
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { port.disconnect(); } catch (_) {}
      reject(new Error('native timeout'));
    }, 8000);
    port.onMessage.addListener((msg) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try { port.disconnect(); } catch (_) {}
      if (msg && msg.ok) resolve(msg);
      else reject(new Error((msg && msg.error) || 'native failed'));
    });
    port.onDisconnect.addListener(() => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      const err = (chrome.runtime.lastError && chrome.runtime.lastError.message) || 'native disconnected';
      reject(new Error(err));
    });
    port.postMessage(payload);
  });
}

function saveToNative(ctx) {
  const text = JSON.stringify(ctx, null, 2);
  return sendNative({ action: 'save', context: ctx }).then((msg) => ({
    text: text,
    path: msg.path,
    via: 'project'
  }));
}

async function appendRuntimeLog(event) {
  const payload = event && typeof event === 'object' ? event : { op: 'log', raw: String(event) };
  try {
    const reply = await sendNative({ action: 'log', event: payload });
    if (reply && reply.path) {
      chrome.storage.local.set({ lastLogPath: reply.path });
    }
    return { ok: true, path: reply.path, via: 'native' };
  } catch (err) {
    const row = Object.assign({ persist_error: String(err && err.message ? err.message : err) }, payload);
    chrome.storage.local.get({ runtimeLogs: [] }, (stored) => {
      const logs = (stored.runtimeLogs || []).concat(row).slice(-80);
      chrome.storage.local.set({ runtimeLogs: logs });
    });
    return { ok: false, via: 'storage', error: String(err && err.message ? err.message : err) };
  }
}

async function persistContext(ctx) {
  const errors = [];
  try {
    return await saveToNative(ctx);
  } catch (err) {
    errors.push('native: ' + (err && err.message ? err.message : err));
  }
  try {
    return await saveToReceiver(ctx);
  } catch (err) {
    errors.push('receiver: ' + (err && err.message ? err.message : err));
  }
  try {
    return await saveToBoundFolder(ctx);
  } catch (err) {
    errors.push('folder: ' + (err && err.message ? err.message : err));
  }
  return {
    text: JSON.stringify(ctx, null, 2),
    path: '',
    via: 'none',
    error: errors.join(' | ')
  };
}

async function loadProfile() {
  try {
    const msg = await sendNative({ action: 'get_profile' });
    if (msg && msg.data) {
      return { data: msg.data, field_rules: msg.field_rules || [] };
    }
  } catch (_) {
    /* fall back to packaged file */
  }
  const stamp = Date.now();
  const url = chrome.runtime.getURL('profile.json') + '?t=' + stamp;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error('缺少 profile.json，请运行 python bin/sync_autofill_profile.py');
  }
  const data = await res.json();
  let field_rules = [];
  try {
    const rr = await fetch(chrome.runtime.getURL('field-map-rules.json') + '?t=' + stamp, { cache: 'no-store' });
    if (rr.ok) field_rules = await rr.json();
  } catch (_) { /* optional */ }
  return { data: data, field_rules: field_rules };
}

async function injectContent(tabId) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      files: CONTENT_JS
    });
  } catch (_) {
    /* 受限页（chrome://）会失败，由调用方处理 */
  }
  try {
    await chrome.scripting.insertCSS({
      target: { tabId, allFrames: true },
      files: CONTENT_CSS
    });
  } catch (_) {
    /* ignore */
  }
}

async function broadcast(tabId, message) {
  let frames = [{ frameId: 0 }];
  try {
    const listed = await chrome.webNavigation.getAllFrames({ tabId });
    if (listed && listed.length) frames = listed;
  } catch (_) {
    /* no webNavigation */
  }
  const results = [];
  for (const frame of frames) {
    try {
      const reply = await chrome.tabs.sendMessage(tabId, message, { frameId: frame.frameId });
      if (reply) results.push(reply);
    } catch (_) {
      /* frame has no listener */
    }
  }
  return results;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'APPEND_LOG') {
    appendRuntimeLog(msg.event || {}).then((res) => sendResponse(res));
    return true;
  }

  if (msg && msg.action === 'GET_PROFILE') {
    loadProfile()
      .then((bundle) => sendResponse({
        ok: true,
        data: bundle.data,
        field_rules: bundle.field_rules || [],
        hot: true
      }))
      .catch((err) => sendResponse({ ok: false, error: String(err && err.message ? err.message : err) }));
    return true;
  }

  if (msg && msg.action === 'RELOAD_EXTENSION') {
    sendResponse({ ok: true });
    setTimeout(() => chrome.runtime.reload(), 50);
    return true;
  }

  if (msg && msg.action === 'CAPTURE_ACTIVE_TAB') {
    chrome.tabs.query({ active: true, currentWindow: true }).then(async (tabs) => {
      const tab = tabs && tabs[0];
      if (!tab || !tab.id) {
        sendResponse({ ok: false, error: '没有活动标签页' });
        return;
      }
      await injectContent(tab.id);
      const results = await broadcast(tab.id, { action: 'CAPTURE' });
      const ctx = mergeCaptures(results);
      if (!ctx) {
        sendResponse({ ok: false, error: '当前页没有捕获到 JD 或表单（可先打开岗位详情/报名页）' });
        return;
      }
      if (tab.url && !ctx.url) ctx.url = tab.url;
      await chrome.storage.local.set({ lastJobContext: ctx });
      const saved = await persistContext(ctx);
      await appendRuntimeLog({
        op: 'capture',
        via: saved.via,
        path: saved.path || '',
        error: saved.error || '',
        title: ctx.title || '',
        url: ctx.url || '',
        fields: (ctx.form_schema || []).length,
        jd_chars: (ctx.jd_text || '').length
      });
      try {
        await chrome.tabs.sendMessage(
          tab.id,
          { action: 'COPY_TEXT', text: saved.text, silent: true },
          { frameId: 0 }
        );
      } catch (_) {
        /* clipboard optional */
      }
      sendResponse({
        ok: true,
        title: ctx.title,
        company: ctx.company,
        fields: (ctx.form_schema || []).length,
        jd_chars: (ctx.jd_text || '').length,
        path: saved.path,
        via: saved.via,
        error: saved.error || ''
      });
    });
    return true;
  }

  if (msg && msg.action === 'FILL_ACTIVE_TAB') {
    chrome.tabs.query({ active: true, currentWindow: true }).then(async (tabs) => {
      const tab = tabs && tabs[0];
      if (!tab || !tab.id) {
        sendResponse({ ok: false, error: '没有活动标签页' });
        return;
      }
      await injectContent(tab.id);
      const results = await broadcast(tab.id, { action: 'AUTOFILL' });
      const filled = results.reduce((n, r) => n + (r && r.count ? r.count : 0), 0);
      sendResponse({ ok: true, filled, frames: results.length });
    });
    return true;
  }

  return false;
});

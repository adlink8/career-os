/**
 * 画像只在扩展进程内读取，不通过 web_accessible_resources 暴露给网页。
 * 填表指令广播到当前标签全部 iframe（北森表单常在子帧）。
 */

try { importScripts('runtime-log.js'); } catch (_) { /* ignore */ }
try { importScripts('overlay-store.js'); } catch (_) { /* ignore */ }

const CONTENT_JS = ['field-map.js', 'runtime-log.js', 'shortcuts.js', 'beisen-fill.js', 'content.js'];
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

function isTestProfile(data) {
  if (!data || typeof data !== 'object') return false;
  const version = String(data.version || '').toLowerCase();
  const name = (((data.universal || {}).personal || {}).name) || '';
  return !!data.test_only || version.indexOf('test') >= 0 || name === '测一填';
}

async function loadOverlay() {
  const Overlay = self.CareerOsOverlay;
  if (!Overlay) return { enabled: false, profile: null };
  return Overlay.loadState();
}

async function loadPackagedJson(name) {
  const url = chrome.runtime.getURL(name) + '?t=' + Date.now();
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(name);
  return res.json();
}

async function loadFieldRules() {
  try {
    const rules = await loadPackagedJson('field-map-rules.json');
    return Array.isArray(rules) ? rules : [];
  } catch (_) {
    return [];
  }
}

async function loadFillPayload(url) {
  const overlay = await loadOverlay();
  const field_rules = await loadFieldRules();
  let bundle = { data: null, field_rules: field_rules };
  try {
    bundle = await loadProfile();
    if (!bundle.field_rules || !bundle.field_rules.length) bundle.field_rules = field_rules;
  } catch (_) {
    bundle = { data: null, field_rules: field_rules };
  }

  if (overlay.enabled && overlay.profile) {
    const name = (((overlay.profile.universal || {}).personal || {}).name) || '';
    if (!name) {
      return {
        ok: true,
        mode: 'setup',
        allow_fill: false,
        reason: '设置页已打开开关但未填姓名。点齿轮填底稿后点「一键导入并启用」。',
        autofill: null,
        profile: overlay.profile,
        field_rules: bundle.field_rules,
        run_id: null,
        overlay: true
      };
    }
    return {
      ok: true,
      mode: 'overlay',
      apply_mode: 'overlay',
      allow_fill: true,
      reason: '',
      autofill: null,
      profile: overlay.profile,
      field_rules: bundle.field_rules,
      run_id: null,
      overlay: true,
      name: name
    };
  }

  try {
    const msg = await sendNative({ action: 'get_fill_payload', url: url || '' });
    if (msg && (msg.ok || msg.mode) && msg.mode !== 'blocked') {
      if (!msg.field_rules) msg.field_rules = bundle.field_rules;
      if (!msg.profile) msg.profile = bundle.data;
      return msg;
    }
  } catch (_) {
    /* 没装 Career OS / Native Host：插件单独用设置页即可 */
  }

  const test = isTestProfile(bundle.data);
  if (test) {
    return {
      ok: true,
      mode: 'test',
      allow_fill: true,
      reason: '测试画像，仅试控件',
      autofill: null,
      profile: bundle.data,
      field_rules: bundle.field_rules,
      run_id: null
    };
  }

  return {
    ok: true,
    mode: 'setup',
    allow_fill: false,
    reason: '只装插件时：点齿轮打开设置，填写或拖入 JSON，再点「一键导入并启用」。不必安装 Career OS。',
    autofill: null,
    profile: bundle.data,
    field_rules: bundle.field_rules,
    run_id: null
  };
}

async function loadProfile() {
  try {
    const msg = await sendNative({ action: 'get_profile' });
    if (msg && msg.data) {
      return { data: msg.data, field_rules: msg.field_rules || [] };
    }
  } catch (_) {
    /* 单独用插件时没有 Native Host */
  }
  try {
    const data = await loadPackagedJson('profile.json');
    return { data: data, field_rules: await loadFieldRules() };
  } catch (_) {
    /* 未打包个人画像 */
  }
  const overlay = await loadOverlay();
  if (overlay.profile) {
    return { data: overlay.profile, field_rules: await loadFieldRules() };
  }
  try {
    const data = await loadPackagedJson('profile.example.json');
    return { data: data, field_rules: await loadFieldRules() };
  } catch (_) {
    throw new Error('没有画像。请打开设置页填写，或拖入 JSON。');
  }
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

  if (msg && msg.action === 'OPEN_OPTIONS') {
    chrome.runtime.openOptionsPage();
    sendResponse({ ok: true });
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

  if (msg && msg.action === 'GET_FILL_PAYLOAD') {
    chrome.tabs.query({ active: true, currentWindow: true }).then(async (tabs) => {
      const tab = tabs && tabs[0];
      const url = msg.url || (tab && tab.url) || '';
      try {
        const payload = await loadFillPayload(url);
        sendResponse(payload);
      } catch (err) {
        sendResponse({ ok: false, mode: 'blocked', allow_fill: false, error: String(err && err.message ? err.message : err) });
      }
    });
    return true;
  }

  if (msg && msg.action === 'IMPORT_FROM_ACTIVE_TAB') {
    const atsRe = /zhiye\.com|italent\.cn|beisen\.com|mokahr\.com|moka\.com|dayee\.com|hotjob\.cn/;
    chrome.tabs.query({}).then(async (all) => {
      const active = (all || []).filter((t) => t.active);
      let tab = active.find((t) => atsRe.test(t.url || ''));
      if (!tab) tab = (all || []).find((t) => atsRe.test(t.url || ''));
      if (!tab || !tab.id) {
        sendResponse({ ok: false, error: '没有打开的北森/Moka 网申页。请先打开报名表再点导入。' });
        return;
      }
      await injectContent(tab.id);
      const results = await broadcast(tab.id, { action: 'READ_FIELD_VALUES' });
      const fields = [];
      results.forEach((r) => {
        if (r && r.ok && Array.isArray(r.fields)) {
          r.fields.forEach((f) => fields.push(f));
        }
      });
      sendResponse({
        ok: fields.length > 0,
        fields: fields,
        count: fields.length,
        title: tab.title || '',
        url: tab.url || ''
      });
    });
    return true;
  }

  if (msg && msg.action === 'MARK_APPLIED') {
    sendNative({
      action: 'mark_applied',
      run_id: msg.run_id,
      coverage: msg.coverage || {}
    }).then((reply) => sendResponse(reply))
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
      const payload = await loadFillPayload(tab.url || '');
      if (!payload.allow_fill) {
        sendResponse({ ok: false, error: payload.reason || '未放行，禁止填充', mode: payload.mode });
        return;
      }
      const results = await broadcast(tab.id, {
        action: 'AUTOFILL',
        fill: payload,
        blankOnly: !!msg.blankOnly
      });
      const filled = results.reduce((n, r) => n + (r && r.count ? r.count : 0), 0);
      const coverage = (results.find((r) => r && r.coverage) || {}).coverage || null;
      sendResponse({
        ok: true,
        filled,
        frames: results.length,
        mode: payload.mode,
        run_id: payload.run_id,
        coverage: coverage
      });
    });
    return true;
  }

  return false;
});

chrome.runtime.onInstalled.addListener((info) => {
  if (info && info.reason === 'install') {
    chrome.runtime.openOptionsPage();
  }
});

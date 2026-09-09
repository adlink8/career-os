document.addEventListener('DOMContentLoaded', async () => {
  const btnFill = document.getElementById('btn-popup-fill');
  const btnCapture = document.getElementById('btn-popup-capture');
  const btnBind = document.getElementById('btn-bind-dir');
  const errEl = document.getElementById('disp-error');

  function showError(msg) {
    errEl.hidden = false;
    errEl.textContent = msg;
  }

  function showLastJob(ctx) {
    if (!ctx) return;
    const label = [ctx.company, ctx.title].filter(Boolean).join(' · ') || ctx.host || '已捕获';
    document.getElementById('disp-job').textContent = label;
  }

  function applyProfile(data) {
    const univ = data.universal || {};
    const app = data.application || {};
    const p = univ.personal || {};
    const edu = (univ.education && univ.education.undergraduate) || {};
    document.getElementById('disp-name').textContent = p.name || '—';
    document.getElementById('disp-school').textContent = [edu.school, edu.degree].filter(Boolean).join(' · ') || '—';
    document.getElementById('disp-target').textContent = app.target_position || '—';
    if (data.test_only) {
      document.getElementById('disp-name').textContent = (p.name || '') + '（测试）';
    }
  }

  function loadProfileView() {
    chrome.runtime.sendMessage({ action: 'GET_PROFILE' }, (res) => {
      if (chrome.runtime.lastError) {
        showError(chrome.runtime.lastError.message);
        return;
      }
      if (!res || !res.ok) {
        showError((res && res.error) || '未找到 profile.json，请运行 python bin/sync_autofill_profile.py');
        return;
      }
      applyProfile(res.data);
    });
  }
  loadProfileView();

  chrome.storage.local.get(['lastJobContext'], (stored) => {
    showLastJob(stored.lastJobContext);
  });

  async function refreshSaveStatus() {
    const el = document.getElementById('disp-save');
    try {
      const res = await fetch('http://127.0.0.1:18765/health');
      if (res.ok) {
        const data = await res.json();
        el.textContent = '接收器 → 项目 captures';
        el.title = data.dir || '';
        return;
      }
    } catch (_) {
      /* offline */
    }
    chrome.storage.local.get(['captureDirName'], (stored) => {
      el.textContent = stored.captureDirName
        ? ('已绑定 ' + stored.captureDirName)
        : '未绑定（会落到浏览器下载）';
    });
  }
  document.getElementById('btn-hot-profile').addEventListener('click', () => {
    loadProfileView();
  });
  document.getElementById('btn-reload-ext').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'RELOAD_EXTENSION' });
  });
  refreshSaveStatus();
  chrome.storage.local.get(['lastLogPath'], (stored) => {
    const el = document.getElementById('disp-log');
    if (el && stored.lastLogPath) {
      el.textContent = stored.lastLogPath.replace(/^.*[\\/]/, '');
      el.title = stored.lastLogPath;
    }
  });

  btnBind.addEventListener('click', async () => {
    try {
      const dir = await window.showDirectoryPicker({
        id: 'career-os-captures',
        mode: 'readwrite'
      });
      await CareerOsDirStore.saveDirHandle(dir);
      chrome.storage.local.set({ captureDirName: dir.name });
      document.getElementById('disp-save').textContent = '已绑定 ' + dir.name;
    } catch (err) {
      if (err && err.name === 'AbortError') return;
      showError(String(err && err.message ? err.message : err));
    }
  });

  async function writeLastContextToPicker() {
    const dir = await window.showDirectoryPicker({
      id: 'career-os-captures',
      mode: 'readwrite'
    });
    await CareerOsDirStore.saveDirHandle(dir);
    chrome.storage.local.set({ captureDirName: dir.name });
    document.getElementById('disp-save').textContent = '已绑定 ' + dir.name;
    const stored = await chrome.storage.local.get(['lastJobContext']);
    if (!stored.lastJobContext) throw new Error('没有可写入的快照');
    const info = await CareerOsDirStore.writeContext(stored.lastJobContext);
    return info.folder + '/' + info.name;
  }

  btnCapture.addEventListener('click', () => {
    btnCapture.textContent = '正在捕获…';
    chrome.runtime.sendMessage({ action: 'CAPTURE_ACTIVE_TAB' }, async (res) => {
      if (chrome.runtime.lastError) {
        showError(chrome.runtime.lastError.message);
        btnCapture.textContent = '捕获当前岗位 JD + 表单';
        return;
      }
      if (!res || !res.ok) {
        showError((res && res.error) || '捕获失败');
        btnCapture.textContent = '捕获当前岗位 JD + 表单';
        return;
      }
      document.getElementById('disp-job').textContent = res.title || '已捕获';
      let via = res.via;
      let path = res.path;
      if (via !== 'project' && via !== 'folder') {
        try {
          path = await writeLastContextToPicker();
          via = 'folder';
        } catch (err) {
          if (!err || err.name !== 'AbortError') {
            showError(
              '未写入项目目录。请先运行 python bin/job_context_receiver.py，或点「绑定」选 data\\job_discovery\\captures。'
              + (res.error ? ' (' + res.error + ')' : '')
            );
          }
          btnCapture.textContent = '捕获当前岗位 JD + 表单';
          return;
        }
      }
      const viaText = via === 'project' ? '已写入项目 captures' : '已写入绑定目录';
      btnCapture.textContent = viaText;
      setTimeout(() => {
        btnCapture.textContent = '捕获当前岗位 JD + 表单';
      }, 2500);
    });
  });

  btnFill.addEventListener('click', () => {
    btnFill.textContent = '正在填充…';
    chrome.runtime.sendMessage({ action: 'FILL_ACTIVE_TAB' }, (res) => {
      if (chrome.runtime.lastError) {
        showError(chrome.runtime.lastError.message);
        btnFill.textContent = '一键填充当前页面表单';
        return;
      }
      if (!res || !res.ok) {
        showError((res && res.error) || '填充失败');
        btnFill.textContent = '一键填充当前页面表单';
        return;
      }
      btnFill.textContent = '已尝试填充 ' + (res.filled || 0) + ' 个字段';
      setTimeout(() => {
        btnFill.textContent = '一键填充当前页面表单';
      }, 2000);
    });
  });
});

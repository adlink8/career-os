document.addEventListener('DOMContentLoaded', async () => {
  const btnFill = document.getElementById('btn-popup-fill');
  const trackSelect = document.getElementById('popup-track-select');

  let tracks = {};
  let currentTrackId = 'ops';

  try {
    const res = await fetch(chrome.runtime.getURL('profile.json'));
    const data = await res.json();
    if (data) {
      tracks = data.tracks;
      const univ = data.universal;
      document.getElementById('disp-name').textContent = `${univ.personal.name} (${univ.personal.gender} · ${univ.personal.age}岁)`;
      document.getElementById('disp-school').textContent = `${univ.education.undergraduate.school} · ${univ.education.undergraduate.degree}`;

      // 读取持久化偏好
      chrome.storage.local.get(['selectedTrack'], (stored) => {
        if (stored.selectedTrack && tracks[stored.selectedTrack]) {
          currentTrackId = stored.selectedTrack;
        } else {
          currentTrackId = data.default_track || 'ops';
        }
        trackSelect.value = currentTrackId;
        refreshTrackDisplay();
      });
    }
  } catch (e) {
    console.error('加载 profile.json 出错:', e);
  }

  function refreshTrackDisplay() {
    const t = tracks[currentTrackId];
    if (t) {
      document.getElementById('disp-target').textContent = t.target_position;
      document.getElementById('disp-proj').textContent = t.projects && t.projects[0] ? t.projects[0].name : '';
    }
  }

  trackSelect.addEventListener('change', async (e) => {
    currentTrackId = e.target.value;
    chrome.storage.local.set({ selectedTrack: currentTrackId });
    refreshTrackDisplay();

    // 通知当前活动标签页更新
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      chrome.tabs.sendMessage(tab.id, { action: 'CHANGE_TRACK', track: currentTrackId });
    }
  });

  btnFill.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;

    btnFill.textContent = '⏳ 正在智能填充...';
    chrome.tabs.sendMessage(tab.id, { action: 'AUTOFILL', track: currentTrackId }, (response) => {
      btnFill.textContent = '✅ 填充已完成！';
      setTimeout(() => {
        btnFill.innerHTML = '<span>🚀</span> 一键填充当前页面表单';
      }, 2000);
    });
  });
});

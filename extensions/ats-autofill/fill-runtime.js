/**
 * 校招网申站点识别 + 等表单 + 点「添加」。
 * 不自动点提交。大厂自建站走 generic，需用户「在当前页启用」。
 */
(function (root) {
  'use strict';

  function detect(href, hostname, hash) {
    var host = String(hostname || '').toLowerCase();
    var url = String(href || '');
    var h = String(hash || '');
    if (!h && url.indexOf('#') !== -1) h = url.slice(url.indexOf('#'));
    if (/zhiye\.com|italent\.cn|beisen\.com/.test(host)) {
      return { ats: 'beisen', label: '北森' };
    }
    if (/mokahr\.com|moka\.com/.test(host)) {
      return { ats: 'moka', label: 'Moka' };
    }
    if (/dayee\.com/.test(host)) return { ats: 'dayee', label: '大易' };
    if (/gllue\.com/.test(host)) return { ats: 'gllue', label: '孤鹿' };
    if (/hotjob\.cn/.test(host)) return { ats: 'hotjob', label: '热招' };
    if (/feishu\.cn|larkoffice\.com/.test(host)) return { ats: 'feishu', label: '飞书招聘' };
    if (/nowcoder\.com/.test(host)) return { ats: 'nowcoder', label: '牛客' };
    if (/zhipin\.com|zhaopin\.com|51job\.com|liepin\.com|lagou\.com|shixiseng\.com/.test(host)) {
      return { ats: 'portal', label: '招聘门户' };
    }
    return { ats: 'generic', label: '通用' };
  }

  function isApplyPage(site, href, hash) {
    var url = String(href || '');
    var h = String(hash || '');
    if (!h && url.indexOf('#') !== -1) h = url.slice(url.indexOf('#'));
    var ats = (site && site.ats) || detect(href, '', h).ats;
    if (ats === 'moka') {
      return /\/job\/[^/]+\/apply/i.test(h) || /\/apply\/[^/]+\/form/i.test(url);
    }
    if (ats === 'beisen') {
      return /\/form|\/apply|campus\/detail/i.test(url + h);
    }
    return true;
  }

  function notApplyMessage(site) {
    if (site && site.ats === 'moka') {
      return '这是 Moka 职位详情。请点「申请」进入报名表（地址带 /apply）再一键填充';
    }
    return '当前页还不是报名表，请进入填写页再试';
  }

  function rowCount(arr) {
    if (!Array.isArray(arr)) return 0;
    var n = 0;
    arr.forEach(function (row) {
      if (!row || typeof row !== 'object') return;
      var ok = Object.keys(row).some(function (k) {
        return String(row[k] == null ? '' : row[k]).trim() !== '';
      });
      if (ok) n += 1;
    });
    return n;
  }

  function extraClicks(need) {
    return Math.max(0, (need || 0) - 1);
  }

  function expandPlan(profile) {
    var app = (profile && profile.application) || {};
    var edu = (profile && profile.universal && profile.universal.education) || {};
    var eduNeed = rowCount(edu.records);
    if (!eduNeed) {
      if (edu.undergraduate && (edu.undergraduate.school || edu.undergraduate.major)) eduNeed += 1;
      if (edu.junior_college && (edu.junior_college.school || edu.junior_college.major)) eduNeed += 1;
    }
    if (!eduNeed) eduNeed = 1;
    return {
      edu: extraClicks(eduNeed),
      intern: extraClicks(rowCount(app.internships)),
      projects: extraClicks(rowCount(app.projects)),
      campus: extraClicks(rowCount(app.campus_roles) + rowCount(app.campus_practices)),
      awards: extraClicks(rowCount(app.award_records)),
      certs: extraClicks(rowCount(app.certificate_records)),
      family: extraClicks(rowCount(app.family_members)),
      training: extraClicks(rowCount(app.training_records))
    };
  }

  function classifyAdd(el) {
    var node = el;
    var i;
    for (i = 0; i < 10 && node; i++) {
      var prev = node.previousElementSibling;
      while (prev) {
        var t = String(prev.textContent || '').replace(/\s+/g, ' ').trim();
        if (t && t.length < 24) {
          if (/项目/.test(t)) return 'projects';
          if (/实习|工作经历/.test(t)) return 'intern';
          if (/教育/.test(t)) return 'edu';
          if (/家庭/.test(t)) return 'family';
          if (/培训/.test(t)) return 'training';
          if (/校园|在校|实践|职务/.test(t)) return 'campus';
          if (/证书/.test(t)) return 'certs';
          if (/获奖/.test(t)) return 'awards';
        }
        prev = prev.previousElementSibling;
      }
      node = node.parentElement;
    }
    return '';
  }

  function findAddButtons(doc) {
    if (!doc || !doc.querySelectorAll) return [];
    var out = [];
    doc.querySelectorAll('button, a, [role="button"], span, div').forEach(function (el) {
      if (el.closest && el.closest('#career-os-floating-root')) return;
      var raw = String(el.textContent || '').trim();
      var t = raw.replace(/\s+/g, '');
      if (t !== '添加' && t !== '+添加' && t !== '添加一段') return;
      if (raw.length > 12) return;
      out.push(el);
    });
    return out;
  }

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function nearbyLabel(el) {
    if (!el) return '';
    function clean(t) {
      t = String(t || '').replace(/\s+/g, ' ').trim();
      t = t.replace(/^请输入\d*位?/, '').replace(/请输入|请选择|请填写/g, '').trim();
      if (!t || t.length > 20) return '';
      if (/首页|了解先导|投递记录|上传简历|预览并提交|搜索职位|立即投递|我的简历/.test(t)) return '';
      return t;
    }
    var doc = el.ownerDocument;
    var labelled = el.getAttribute && el.getAttribute('aria-labelledby');
    if (labelled && doc && doc.getElementById) {
      var by = clean((doc.getElementById(labelled) || {}).textContent);
      if (by) return by;
    }
    var aria = clean(el.getAttribute && el.getAttribute('aria-label'));
    if (aria) return aria;
    var node = el;
    var depth = 0;
    while (node && depth < 8) {
      var prev = node.previousElementSibling;
      while (prev) {
        var c = clean(prev.textContent);
        if (c) return c;
        var inner = prev.querySelector && prev.querySelector('.el-form-item__label, .ant-form-item-label, .bs-form-item-label, label');
        if (inner) {
          c = clean(inner.textContent);
          if (c) return c;
        }
        prev = prev.previousElementSibling;
      }
      var td = node.tagName === 'TD' ? node : null;
      if (!td && node.parentElement && node.parentElement.tagName === 'TD') td = node.parentElement;
      if (td && td.parentElement) {
        var th = td.parentElement.querySelector('th');
        var ht = th && clean(th.textContent);
        if (ht) return ht;
      }
      node = node.parentElement;
      depth += 1;
    }
    return '';
  }

  function formReady(doc) {
    if (!doc || !doc.querySelectorAll) return false;
    var hit = 0;
    doc.querySelectorAll('input:not([type="hidden"]):not([type="file"]), textarea').forEach(function (el) {
      if (el.id === 'moka-version') return;
      var blob = [el.placeholder, el.getAttribute('aria-label'), el.parentElement && el.parentElement.textContent]
        .join(' ')
        .slice(0, 80);
      if (/姓名|手机|邮箱|学校/.test(blob)) hit += 1;
    });
    return hit >= 1;
  }

  function waitForForm(doc, timeoutMs) {
    timeoutMs = timeoutMs || 1200;
    return new Promise(function (resolve) {
      if (formReady(doc)) {
        resolve(true);
        return;
      }
      var started = Date.now();
      var timer = setInterval(function () {
        if (formReady(doc) || Date.now() - started > timeoutMs) {
          clearInterval(timer);
          resolve(formReady(doc));
        }
      }, 200);
    });
  }

  async function expandRepeatable(doc, profile) {
    if (!doc) return 0;
    var plan = expandPlan(profile);
    var remain = {
      edu: plan.edu,
      intern: plan.intern,
      projects: plan.projects,
      campus: plan.campus,
      awards: plan.awards,
      certs: plan.certs,
      family: plan.family,
      training: plan.training
    };
    var clicks = 0;
    var guard = 0;
    while (guard < 8) {
      guard += 1;
      var buttons = findAddButtons(doc);
      var did = false;
      var i;
      for (i = 0; i < buttons.length; i++) {
        var kind = classifyAdd(buttons[i]);
        if (!kind || !remain[kind]) continue;
        try { buttons[i].click(); } catch (_) { continue; }
        remain[kind] -= 1;
        clicks += 1;
        did = true;
        await sleep(60);
        break;
      }
      if (!did) break;
    }
    return clicks;
  }

  async function revealForm(doc, win) {
    if (!doc) return;
    win = win || doc.defaultView;
    var root = doc.scrollingElement || doc.documentElement;
    var body = doc.body;
    var max = Math.max(
      (root && root.scrollHeight) || 0,
      (body && body.scrollHeight) || 0
    );
    var view = (win && win.innerHeight) || 800;
    var stops = [0, 0.2, 0.4, 0.6, 0.8, 1];
    var i;
    for (i = 0; i < stops.length; i++) {
      var y = Math.max(0, Math.floor((max - view) * stops[i]));
      if (win && win.scrollTo) win.scrollTo(0, y);
      else if (root) root.scrollTop = y;
      await sleep(160);
    }
    if (doc.querySelectorAll) {
      doc.querySelectorAll('[class*="scroll"], [class*="content"], .ant-drawer-body, .el-dialog__body').forEach(function (p) {
        try {
          if (p.scrollHeight > p.clientHeight + 40) p.scrollTop = p.scrollHeight;
        } catch (_) { /* ignore */ }
      });
    }
    await sleep(180);
    if (win && win.scrollTo) win.scrollTo(0, 0);
  }

  root.CareerOsFillRuntime = {
    detect: detect,
    isApplyPage: isApplyPage,
    notApplyMessage: notApplyMessage,
    rowCount: rowCount,
    extraClicks: extraClicks,
    expandPlan: expandPlan,
    classifyAdd: classifyAdd,
    findAddButtons: findAddButtons,
    formReady: formReady,
    waitForForm: waitForForm,
    expandRepeatable: expandRepeatable,
    revealForm: revealForm,
    nearbyLabel: nearbyLabel
  };
})(typeof self !== 'undefined' ? self : this);

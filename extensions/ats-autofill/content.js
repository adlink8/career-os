/**
 * Career OS — ATS 网申自动填表助手 Content Script
 * 架构：【通用数据稳定层】+【岗位 JD / 简历轨道动态绑定层】
 * 支持根据当前网页职位自动识别或手动一键切换简历版本
 */

(function () {
  'use strict';

  let rawData = null;
  let universalData = null;
  let tracks = {};
  let currentTrackId = 'ops';
  let isPanelOpen = false;

  // 0. 判断是否为校招、网申或主流 ATS 招聘页面
  function isRecruitmentPage() {
    const host = window.location.hostname.toLowerCase();
    const url = window.location.href.toLowerCase();
    const title = (document.title || '').toLowerCase();

    // 1. 绝对排除日常无关网站（强防打扰）
    const blacklist = [
      'github.com', 'bilibili.com', 'youtube.com', 'google.', 'baidu.',
      'zhihu.com', 'weibo.com', 'taobao.com', 'jd.com', 'douyin.com',
      'v2ex.com', 'twitter.com', 'x.com', 'reddit.com', 'bing.com',
      'chatgpt.com', 'deepseek.com', 'claude.ai', 'localhost', '127.0.0.1'
    ];
    if (blacklist.some(b => host.includes(b))) return false;

    // 2. 主流招聘 ATS 系统主域名（北森、Moka、大易、用友等必中）
    const atsDomains = [
      'zhiye.com', 'italent.cn', 'beisen.com', 'mokahr.com',
      'moka.com', 'dayee.com', 'hotjob.cn', 'gllue.com',
      'zhaopin.com', '51job.com', 'bosszhipin.com', 'lagou.com',
      'liepin.com', 'nowcoder.com', 'shixiseng.com'
    ];
    if (atsDomains.some(d => host.endsWith(d) || host.includes('.' + d))) return true;

    // 3. 企业自建招聘门户的常见二级域名（如 campus.xxx.com, jobs.xxx.com）
    if (/^(campus|career|careers|job|jobs|zhaopin|join|hr)\./.test(host)) return true;

    // 4. 常见校招、网申 URL 路径
    if (/\/(campus|apply|jobs?|careers?|recruitment|school|xiaozhao|portal\/campus)/.test(url)) return true;

    // 5. 网页标题命中校招核心关键词
    if (/(校招|校园招聘|应届生|网申|职位申请|填写简历|个人简历|投递简历|应聘表单|毕业生招聘)/.test(title)) return true;

    return false;
  }

  // 1. 载入 profile.json 并初始化轨道
  async function loadProfile() {
    try {
      const url = chrome.runtime.getURL('profile.json');
      const res = await fetch(url);
      rawData = await res.json();
      universalData = rawData.universal;
      tracks = rawData.tracks;
      currentTrackId = rawData.default_track || 'ops';

      // 检查本地持久化的轨道选择
      chrome.storage.local.get(['selectedTrack'], (stored) => {
        if (stored.selectedTrack && tracks[stored.selectedTrack]) {
          currentTrackId = stored.selectedTrack;
        } else {
          // 智能感知当前页面 JD 岗位类别
          autoDetectTrack();
        }
        updateUI();
      });

      console.log('[Career OS] 成功载入画像多轨道数据，当前轨道:', currentTrackId);
    } catch (e) {
      console.error('[Career OS] 载入 profile.json 失败:', e);
    }
  }

  // 2. 智能感知当前网页岗位 JD 关键词，自动切换匹配的简历版本
  function autoDetectTrack() {
    const pageText = (
      document.title + ' ' +
      (document.querySelector('h1, .job-title, .position-title, .job-name, .post-name, [class*="jobTitle"], [class*="positionTitle"]')?.textContent || '')
    ).toLowerCase();

    for (const [tId, tData] of Object.entries(tracks)) {
      if (tData.keywords && tData.keywords.some(kw => pageText.includes(kw.toLowerCase()))) {
        currentTrackId = tId;
        console.log(`[Career OS] 智能匹配到目标岗位轨道: [${tData.name}] (匹配词来自页面标题/JD)`);
        break;
      }
    }
  }

  // 3. 突破 Vue/React 响应式数据拦截
  function setNativeValue(element, value) {
    if (!element || value === undefined || value === null) return false;

    const isTextarea = element.tagName.toLowerCase() === 'textarea';
    const prototype = isTextarea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, value);
    } else if (valueSetter) {
      valueSetter.call(element, value);
    } else {
      element.value = value;
    }

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
    return true;
  }

  // 4. 提取输入框周围的上下文
  function getFieldContext(el) {
    let context = '';
    if (el.placeholder) context += ' ' + el.placeholder;
    if (el.name) context += ' ' + el.name;
    if (el.id) context += ' ' + el.id;
    if (el.getAttribute('aria-label')) context += ' ' + el.getAttribute('aria-label');
    if (el.getAttribute('data-automation')) context += ' ' + el.getAttribute('data-automation');

    let parent = el.parentElement;
    let depth = 0;
    while (parent && depth < 4) {
      const labelEl = parent.querySelector('label, .el-form-item__label, .ant-form-item-label, .bs-form-item-label, .title, .item-label, th');
      if (labelEl) {
        context += ' ' + labelEl.textContent;
        break;
      }
      depth++;
      parent = parent.parentElement;
    }

    let prev = el.previousElementSibling;
    if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'SPAN' || prev.tagName === 'DIV')) {
      context += ' ' + prev.textContent;
    }

    return context.replace(/\s+/g, ' ').trim();
  }

  // 5. 核心匹配引擎：通用字段稳定不变，JD 定制字段绑定当前轨道
  function matchAndFillField(el, univ, track) {
    if (el.type === 'hidden' || el.type === 'file' || el.disabled) return false;

    const ctx = getFieldContext(el);
    const p = univ.personal;
    const edu = univ.education.undergraduate;
    const isTextarea = el.tagName.toLowerCase() === 'textarea';
    const proj = track.projects && track.projects.length > 0 ? track.projects[0] : null;

    // ==========================================
    // A. 【动态层】：根据当前岗位 JD / 简历轨道绑定的字段
    // ==========================================

    // 1. 自我评价 / 个人总结（对齐当前 JD 优势）
    if (isTextarea && /(自我评价|个人总结|自我介绍|个人特质|个人优势|优势与特长|评语)/.test(ctx)) {
      return setNativeValue(el, track.self_evaluation);
    }

    // 2. 专业技能（对齐当前 JD 技能重点）
    if (isTextarea && /(IT技能|专业技能|技能特长|掌握技能|技能描述|技术特长|个人技能|业务技能|技能清单)/.test(ctx)) {
      return setNativeValue(el, track.skills_summary);
    }
    if (!isTextarea && /(熟练技能|熟练掌握|精通技能)/.test(ctx)) {
      return setNativeValue(el, track.skills_proficient);
    }
    if (!isTextarea && /(熟悉技能|掌握技能|了解技能)/.test(ctx)) {
      return setNativeValue(el, track.skills_familiar);
    }

    // 3. 期望岗位 / 求职意向（对齐当前岗位）
    if (/(求职意向|期望岗位|目标岗位|应聘职位)/.test(ctx)) {
      return setNativeValue(el, track.target_position);
    }
    if (/(期望薪资|期望月薪|期望年薪)/.test(ctx)) {
      return setNativeValue(el, track.expected_salary);
    }
    if (/(期望工作地|意向城市|期望城市)/.test(ctx)) {
      return setNativeValue(el, track.target_cities);
    }

    // 4. 项目经历相关（对齐当前轨道的重点代表项目）
    if (!isTextarea && /(项目经理|项目负责人|担任角色|项目角色|项目职务|担任职务|项目职位|^角色$|^职务$)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.role : '核心开发 / 项目负责人');
    }
    if (!isTextarea && /(项目名称|项目名)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.name : '');
    }
    if (!isTextarea && /(技术栈|核心技术|关键技术|涉及技术)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.keywords : '');
    }
    if (!isTextarea && /(项目开始时间|项目起始年月|项目开始)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.start_date : '2024-03');
    }
    if (!isTextarea && /(项目结束时间|项目结束年月|项目结束)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.end_date : '至今');
    }
    if (isTextarea && /(职责描述|项目职责|工作职责|负责内容)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.duty : '');
    }
    if (isTextarea && /(项目业绩|项目成果|工作业绩|量化成果)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.achievement : '');
    }
    if (isTextarea && /(项目描述|项目内容|项目详情|项目经验|项目概述)/.test(ctx)) {
      return setNativeValue(el, proj ? proj.full_text : track.self_evaluation);
    }

    // ==========================================
    // B. 【通用稳定层】：永不随 JD 变动的客观事实
    // ==========================================

    // 5. 个人爱好 / 特长
    if (/(个人爱好|兴趣爱好|业余爱好|特长爱好|爱好|特长)/.test(ctx)) {
      return setNativeValue(el, univ.hobbies);
    }

    // 6. 获奖荣誉 / 竞赛奖励
    if (/(获奖情况|所获荣誉|奖励情况|竞赛经历|荣誉奖项|获奖经历|获得荣誉|奖项)/.test(ctx)) {
      return setNativeValue(el, univ.awards);
    }

    // 7. 职业资格与证书
    if (/(职业资格|所持证书|资格证书|获得证书|证书名称|^证书$)/.test(ctx)) {
      return setNativeValue(el, univ.certificates);
    }

    // 8. 外语水平与能力
    if (/(外语能力|英语水平|外语水平|语言能力|英语等级|CET|四六级)/.test(ctx)) {
      return setNativeValue(el, univ.languages);
    }

    // 9. 姓名 / 电话 / 邮箱
    if (/(真实姓名|候选人姓名|您的姓名|^姓名$|英文名)/.test(ctx)) {
      return setNativeValue(el, p.name);
    }
    if (/(手机号码|联系电话|移动电话|^手机$|^电话$|手机号)/.test(ctx)) {
      return setNativeValue(el, p.phone);
    }
    if (/(电子邮箱|个人邮箱|联系邮箱|^邮箱$|email)/i.test(ctx)) {
      return setNativeValue(el, p.email);
    }

    // 10. 身份证 / 民族 / 健康状况
    if (/(身份证号码|证件号码|身份证号|证件号)/.test(ctx)) {
      return setNativeValue(el, p.id_card);
    }
    if (/(^民族$)/.test(ctx)) {
      return setNativeValue(el, p.ethnicity);
    }
    if (/(健康状况|^健康$)/.test(ctx)) {
      return setNativeValue(el, p.health);
    }

    // 11. 院校 / 专业 / 学历 / 时间
    if (/(毕业院校|就读院校|最高学历院校|毕业学校|^学校$|院校名称)/.test(ctx)) {
      return setNativeValue(el, edu.school);
    }
    if (/(所学专业|专业名称|^专业$|主修专业)/.test(ctx)) {
      return setNativeValue(el, edu.major);
    }
    if (/(最高学历|^学历$|^学位$|学历层次|文化程度)/.test(ctx)) {
      return setNativeValue(el, edu.degree);
    }
    if (/(预计毕业时间|毕业年月|毕业时间|毕业年份)/.test(ctx)) {
      return setNativeValue(el, edu.graduation);
    }
    if (/(入学时间|就读开始时间|起始年月|入学年月)/.test(ctx)) {
      return setNativeValue(el, edu.start_date);
    }

    // 12. 出生日期 / 年龄
    if (/(出生日期|出生年月|^生日$)/.test(ctx)) {
      return setNativeValue(el, p.birth_date);
    }
    if (/(^年龄$|周岁)/.test(ctx)) {
      return setNativeValue(el, p.age);
    }

    // 13. 现居地与户籍
    if (/(现居住地址|详细地址|家庭住址|联系地址)/.test(ctx)) {
      return setNativeValue(el, p.current_address);
    }
    if (/(现居住地|当前所在地|现所在城市|^现居地$|^现居$)/.test(ctx)) {
      return setNativeValue(el, p.current_city);
    }
    if (/(^籍贯$|生源地|户口所在地|^户籍$)/.test(ctx)) {
      return setNativeValue(el, p.native_place);
    }
    if (/(政治面貌)/.test(ctx)) {
      return setNativeValue(el, p.political_status);
    }

    // 14. 到岗时间与实习时长
    if (/(到岗时间|最快到岗|可到岗时间|何时到岗)/.test(ctx)) {
      return setNativeValue(el, p.available_time);
    }
    if (/(实习周期|实习时长|可实习时长|连续实习)/.test(ctx)) {
      return setNativeValue(el, p.internship_duration);
    }
    if (/(每周出勤|每周实习天数|出勤天数)/.test(ctx)) {
      return setNativeValue(el, p.days_per_week);
    }

    // 15. 紧急联系人
    if (/(紧急联系人姓名|紧急联系人)/.test(ctx)) {
      return setNativeValue(el, p.emergency_contact);
    }
    if (/(紧急联系人电话|紧急电话|紧急联系电话)/.test(ctx)) {
      return setNativeValue(el, p.emergency_phone);
    }
    if (/(与紧急联系人关系|与本人关系|亲属关系|家庭关系|^关系$)/.test(ctx)) {
      return setNativeValue(el, p.emergency_relation);
    }

    return false;
  }

  // 6. 处理单选框
  function fillRadios(univ) {
    let filledCount = 0;
    const radios = document.querySelectorAll('input[type="radio"]');
    radios.forEach((radio) => {
      const label = radio.parentElement ? radio.parentElement.textContent.trim() : '';
      const ctx = getFieldContext(radio);

      if (/(性别)/.test(ctx) || label === '男') {
        if (label.includes('男') && !radio.checked) {
          radio.click();
          radio.dispatchEvent(new Event('change', { bubbles: true }));
          filledCount++;
        }
      }
      if (/(婚姻)/.test(ctx) && label.includes('未婚') && !radio.checked) {
        radio.click();
        radio.dispatchEvent(new Event('change', { bubbles: true }));
        filledCount++;
      }
    });
    return filledCount;
  }

  // 7. 执行自动填充
  function executeAutofill() {
    if (!universalData || !tracks[currentTrackId]) {
      showToast('⚠️ 正在载入画像数据，请稍后重试');
      return;
    }

    const activeTrack = tracks[currentTrackId];
    let count = 0;
    const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="file"]), textarea');

    inputs.forEach((el) => {
      if (matchAndFillField(el, universalData, activeTrack)) {
        count++;
      }
    });

    count += fillRadios(universalData);

    showToast(`⚡ 已按【${activeTrack.name}】版本填入 ${count} 个字段！`);
    console.log(`[Career OS] 自动填表完成，当前版本: [${activeTrack.name}]，填充字段数: ${count}`);
  }

  // 8. Toast 提示
  function showToast(msg) {
    const existing = document.querySelector('.career-os-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'career-os-toast';
    toast.innerHTML = `<span>🚀</span><span>${msg}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  // 9. 复制到剪贴板
  function copyToClipboard(text, label) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`已复制: ${label}`);
    }).catch(() => {
      showToast(`复制失败`);
    });
  }

  // 10. 注入悬浮 UI（带岗位轨道切换器）
  function injectFloatingUI() {
    if (document.getElementById('career-os-floating-root')) return;

    const root = document.createElement('div');
    root.id = 'career-os-floating-root';

    root.innerHTML = `
      <div class="career-os-panel" id="career-os-panel" style="display: none;">
        <div class="career-os-header">
          <div class="career-os-title">
            <span>⚡</span> Career OS 填表助手
            <span class="career-os-badge" id="career-os-track-badge">DevOps版</span>
          </div>
          <div class="career-os-close" id="career-os-close">✕</div>
        </div>
        <div class="career-os-body">
          <!-- 岗位轨道切换栏 -->
          <div style="background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 8px 10px;">
            <div style="font-size: 11px; font-weight: 700; color: #4338ca; margin-bottom: 4px;">🎯 当前投递岗位 / 简历版本绑定：</div>
            <select id="career-os-track-select" style="width: 100%; padding: 6px 8px; border-radius: 6px; border: 1px solid #a5b4fc; background: #ffffff; font-size: 12px; font-weight: 600; color: #312e81; outline: none; cursor: pointer;">
              <option value="ops">🎯 DevOps / Linux 运维工程师</option>
              <option value="iot">🔌 IoT / 智能硬件与嵌入式技术支持</option>
              <option value="ai_infra">🤖 AI Agent / 研发效能与数据工程</option>
              <option value="tech_support">💼 技术支持工程师 (FAE / IT Support)</option>
            </select>
          </div>

          <button class="career-os-btn-primary" id="career-os-fill-btn">
            <span>🚀</span> 一键填充当前页面表单
          </button>

          <!-- 动态概览卡片 -->
          <div class="career-os-info-card">
            <div class="career-os-info-row">
              <span class="career-os-info-label">通用候选人</span>
              <span class="career-os-info-val" id="career-os-val-name">李硕研 (男 · 23岁)</span>
            </div>
            <div class="career-os-info-row">
              <span class="career-os-info-label">通用院校</span>
              <span class="career-os-info-val">常州大学 · 本科</span>
            </div>
            <div class="career-os-info-row">
              <span class="career-os-info-label">绑定意向</span>
              <span class="career-os-info-val" id="career-os-disp-target" style="color: #4f46e5;">运维工程师 / DevOps</span>
            </div>
            <div class="career-os-info-row">
              <span class="career-os-info-label">首推项目</span>
              <span class="career-os-info-val" id="career-os-disp-proj" style="font-size: 11px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">NovelMind 稳定性治理</span>
            </div>
          </div>

          <div class="career-os-section-title">📋 当前轨道核心文本快捷复制</div>
          <div class="career-os-copy-list" id="career-os-copy-container">
            <!-- 动态生成当前轨道的复制项 -->
          </div>
        </div>
      </div>

      <div class="career-os-fab" id="career-os-fab" title="点击展开 Career OS 自动填表助手">
        <span class="career-os-fab-icon">⚡</span>
        <span>Career OS 填表</span>
      </div>
    `;

    document.body.appendChild(root);

    // 事件绑定
    const fab = document.getElementById('career-os-fab');
    const panel = document.getElementById('career-os-panel');
    const closeBtn = document.getElementById('career-os-close');
    const fillBtn = document.getElementById('career-os-fill-btn');
    const trackSelect = document.getElementById('career-os-track-select');

    fab.addEventListener('click', () => {
      isPanelOpen = !isPanelOpen;
      panel.style.display = isPanelOpen ? 'flex' : 'none';
      if (isPanelOpen) updateUI();
    });

    closeBtn.addEventListener('click', () => {
      isPanelOpen = false;
      panel.style.display = 'none';
    });

    fillBtn.addEventListener('click', () => {
      executeAutofill();
    });

    trackSelect.addEventListener('change', (e) => {
      currentTrackId = e.target.value;
      chrome.storage.local.set({ selectedTrack: currentTrackId });
      updateUI();
      showToast(`已切换至【${tracks[currentTrackId].name}】版本`);
    });
  }

  // 11. 刷新 UI 状态
  function updateUI() {
    const trackSelect = document.getElementById('career-os-track-select');
    const badge = document.getElementById('career-os-track-badge');
    const dispTarget = document.getElementById('career-os-disp-target');
    const dispProj = document.getElementById('career-os-disp-proj');

    if (trackSelect && currentTrackId) {
      trackSelect.value = currentTrackId;
    }

    const t = tracks[currentTrackId];
    if (t) {
      if (badge) badge.textContent = t.name.split('/')[0].trim() + '版';
      if (dispTarget) dispTarget.textContent = t.target_position;
      if (dispProj && t.projects && t.projects[0]) dispProj.textContent = t.projects[0].name;
    }

    renderCopyList();
  }

  // 12. 渲染快捷复制列表（深度对齐当前 JD 轨道）
  function renderCopyList() {
    const container = document.getElementById('career-os-copy-container');
    if (!container || !universalData || !tracks[currentTrackId]) return;

    const univ = universalData;
    const t = tracks[currentTrackId];
    const proj1 = t.projects[0] || {};
    const proj2 = t.projects[1] || {};

    const copyItems = [
      { label: `【${t.name}】自我评价`, val: t.self_evaluation, hint: '评价' },
      { label: `【${t.name}】专业技能`, val: t.skills_summary, hint: '技能' },
      { label: `首推项目: ${proj1.name}`, val: proj1.full_text || proj1.description, hint: '项目1' },
      { label: `备选项目: ${proj2.name}`, val: proj2.full_text || proj2.description, hint: '项目2' },
      { label: '常州大学 · 计算机科学与技术', val: `${univ.education.undergraduate.school} ${univ.education.undergraduate.major}`, hint: '学历' },
      { label: '个人爱好与特长', val: univ.hobbies, hint: '爱好' },
      { label: '获奖荣誉与竞赛', val: univ.awards, hint: '荣誉' },
      { label: '外语能力描述', val: univ.languages, hint: '外语' },
      { label: '职业证书', val: univ.certificates, hint: '证书' }
    ];

    container.innerHTML = copyItems.map((item, idx) => `
      <div class="career-os-copy-item">
        <span class="career-os-copy-name" title="${item.val}">${item.label}</span>
        <button class="career-os-copy-btn" data-idx="${idx}">复制</button>
      </div>
    `).join('');

    container.querySelectorAll('.career-os-copy-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.getAttribute('data-idx'), 10);
        const item = copyItems[idx];
        copyToClipboard(item.val, item.label);
      });
    });
  }

  // 13. 监听来自 popup 的切换轨道或填表指令
  chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
    // 用户手动在 popup 中点击触发时，无论什么页面都按需唤醒并注入 UI
    injectFloatingUI();

    if (req.action === 'AUTOFILL') {
      if (req.track && tracks[req.track]) {
        currentTrackId = req.track;
        updateUI();
      }
      executeAutofill();
      sendResponse({ success: true, track: currentTrackId });
    } else if (req.action === 'CHANGE_TRACK') {
      if (req.track && tracks[req.track]) {
        currentTrackId = req.track;
        updateUI();
        sendResponse({ success: true, track: currentTrackId });
      }
    }
  });

  // 初始化：只有确认为校招 / 网申 / ATS 页面时才自动唤醒并注入悬浮球
  loadProfile().then(() => {
    if (isRecruitmentPage()) {
      injectFloatingUI();
      console.log('[Career OS] 检测到校招/招聘页面，已激活自动填表助手。');
    } else {
      console.log('[Career OS] 当前非校招/网申页面，保持静默，不注入任何 UI。');
    }
  });

})();

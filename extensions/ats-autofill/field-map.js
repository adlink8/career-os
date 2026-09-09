/**
 * 表单格子 → 画像槽位。捕获和填表共用，避免再按岗位轨道分支。
 */
(function (root) {
  'use strict';

  function pick(obj, path) {
    return path.split('.').reduce(function (acc, key) {
      return acc == null ? undefined : acc[key];
    }, obj);
  }

  var RULES = [
    { slot: 'application.self_evaluation', textarea: true, re: /自我评价|个人总结|自我介绍|个人特质|个人优势|优势与特长|评语/ },
    { slot: 'application.skills_summary', textarea: true, re: /IT技能|专业技能|技能特长|掌握技能|技能描述|技术特长|个人技能|业务技能|技能清单/ },
    { slot: 'application.skills_proficient', textarea: false, re: /熟练技能|熟练掌握|精通技能/ },
    { slot: 'application.skills_familiar', textarea: false, re: /熟悉技能|掌握技能|了解技能/ },
    { slot: 'application.target_position', re: /求职意向|期望岗位|目标岗位|应聘职位/ },
    { slot: 'application.expected_salary', re: /期望薪资|期望月薪|期望年薪/ },
    { slot: 'application.target_cities', re: /期望工作地|意向城市|期望城市/ },
    { slot: 'application.projects.role', textarea: false, re: /项目经理|项目负责人|担任角色|项目角色|项目职务|担任职务|项目职位|^角色$|^职务$/ },
    { slot: 'application.projects.name', textarea: false, re: /项目名称|项目名/ },
    { slot: 'application.projects.keywords', textarea: false, re: /技术栈|核心技术|关键技术|涉及技术/ },
    { slot: 'application.projects.start_date', textarea: false, re: /项目开始时间|项目起始年月|项目开始/ },
    { slot: 'application.projects.end_date', textarea: false, re: /项目结束时间|项目结束年月|项目结束/ },
    { slot: 'application.projects.duty', textarea: true, re: /职责描述|项目职责|工作职责|负责内容/ },
    { slot: 'application.projects.achievement', textarea: true, re: /项目业绩|项目成果|工作业绩|量化成果/ },
    { slot: 'application.projects.full_text', textarea: true, re: /项目描述|项目内容|项目详情|项目经验|项目概述/ },
    { slot: 'universal.hobbies', re: /个人爱好|兴趣爱好|业余爱好|特长爱好/ },
    { slot: 'universal.awards', re: /获奖情况|所获荣誉|奖励情况|竞赛经历|荣誉奖项|获奖经历|获得荣誉|奖项/ },
    { slot: 'universal.certificates', re: /职业资格|所持证书|资格证书|获得证书|证书名称|^证书$/ },
    { slot: 'universal.languages', re: /外语能力|英语水平|外语水平|语言能力|英语等级|CET|四六级/ },
    { slot: 'universal.personal.name', re: /真实姓名|候选人姓名|您的姓名|^姓名$|英文名/ },
    { slot: 'universal.personal.phone', re: /手机号码|联系电话|移动电话|^手机$|^电话$|手机号/ },
    { slot: 'universal.personal.email', re: /电子邮箱|个人邮箱|联系邮箱|^邮箱$|email/i },
    { slot: 'universal.personal.id_card', re: /身份证号码|证件号码|身份证号|证件号/ },
    { slot: 'universal.personal.ethnicity', re: /民族/ },
    { slot: 'universal.personal.health', re: /健康状况|^健康$/ },
    { slot: 'universal.education.undergraduate.school', re: /毕业院校|就读院校|最高学历院校|毕业学校|^学校$|院校名称/ },
    { slot: 'universal.education.undergraduate.major', re: /所学专业|专业名称|^专业$|主修专业/ },
    { slot: 'universal.education.undergraduate.degree', re: /最高学历|^学历$|^学位$|学历层次|文化程度/ },
    { slot: 'universal.education.undergraduate.graduation', re: /预计毕业时间|毕业年月|毕业时间|毕业年份/ },
    { slot: 'universal.education.undergraduate.start_date', re: /入学时间|就读开始时间|入学年月/ },
    { slot: 'universal.personal.birth_date', re: /出生日期|出生年月|^生日$/ },
    { slot: 'universal.personal.age', re: /年龄|周岁/ },
    { slot: 'universal.personal.current_address', re: /现居住地址|详细地址|家庭住址|联系地址/ },
    { slot: 'universal.personal.current_city', re: /现居住地|当前所在地|现所在城市|^现居地$|^现居$/ },
    { slot: 'universal.personal.native_place', re: /籍贯|生源地|户口所在地|户籍/ },
    { slot: 'universal.personal.political_status', re: /政治面貌/ },
    { slot: 'universal.personal.available_time', re: /到岗时间|最快到岗|可到岗时间|何时到岗/ },
    { slot: 'universal.personal.internship_duration', re: /实习周期|实习时长|可实习时长|连续实习/ },
    { slot: 'universal.personal.days_per_week', re: /每周出勤|每周实习天数|出勤天数/ },
    { slot: 'universal.personal.emergency_phone', re: /紧急联系人电话|紧急联系电话|紧急电话/ },
    { slot: 'universal.personal.emergency_contact', re: /紧急联系人姓名|紧急联系人/ },
    { slot: 'universal.personal.emergency_relation', re: /与紧急联系人关系|与本人关系|亲属关系|家庭关系|^关系$/ },
    { slot: 'universal.personal.gender', re: /性别/ },
    { slot: 'universal.personal.marriage', re: /婚姻/ }
  ];

  function resolveSlot(ctx, meta) {
    var text = String(ctx || '');
    if (/民族/.test(text) && /大学|学院/.test(text)) {
      return '';
    }
    var isTextarea = !!(meta && meta.isTextarea);
    for (var i = 0; i < RULES.length; i++) {
      var rule = RULES[i];
      if (rule.textarea === true && !isTextarea) continue;
      if (rule.textarea === false && isTextarea) continue;
      if (rule.re.test(text)) return rule.slot;
    }
    return '';
  }

  function projectValue(profile, key, index) {
    var list = pick(profile, 'application.projects') || [];
    var item = list[index] || list[0] || {};
    return item[key] || '';
  }

  function valueForSlot(slot, profile, projectIndex) {
    if (!slot || !profile) return '';
    if (slot.indexOf('application.projects.') === 0) {
      var key = slot.slice('application.projects.'.length);
      return projectValue(profile, key, projectIndex || 0);
    }
    var val = pick(profile, slot);
    if (val == null) return '';
    return String(val).trim();
  }

  function isRealIdCard(value) {
    return /^\d{17}[\dXx]$/.test(String(value || '').trim());
  }

  root.CareerOsFieldMap = {
    resolveSlot: resolveSlot,
    valueForSlot: valueForSlot,
    isRealIdCard: isRealIdCard
  };
})(typeof self !== 'undefined' ? self : this);

# 简历模板(纯模板 · 占位符版)

> 本文件是**纯模板**,不含任何真实个人信息。
> 真实简历由 `general-recruit`(未创建)或人工读取 `config/profile.yml` 生成,落到 `data/cv/cv-real.md`。
> Skill 运行时:读取此模板作为结构骨架,读取 `config/profile.yml` 填充真实数据。
>
> 占位符约定:
> - `{{变量名}}` = 由 profile.yml 字段映射
> - `[说明]` = 人工填写/追问补齐

---

## {{name}}

**求职意向**:{{target_primary}} | {{target_cities}} | 期望薪资 {{salary_min}}-{{salary_max}}k

**联系方式**:[手机号] | [邮箱]

---

## 教育背景

{{school}} | {{major}} | {{degree}} | {{graduation}}毕业

---

## 技能

- **熟练**:{{skills_proficient}}
- **掌握**:{{skills_familiar}}
- **学习中**:{{skills_learning}}

---

## 项目经历

### {{project_1_name}}({{project_1_year}})
- [一句话职责]
- [量化成果,例如:在线率从 X% 提升至 Y%]
- [关键技术/排查过程]

### {{project_2_name}}
- [一句话职责]
- [量化成果]
- [关键技术]

### {{project_3_name}}
- [一句话职责]
- [量化成果]
- [关键技术]

---

## 证书与竞赛

- {{cert_1}}
- [其他证书]

---

## 填写规范

1. **每个项目至少 1 条量化成果**(百分比、数量、时间),没有量化的项目不写。
2. **技能分级严格对齐 profile.yml**(proficient/familiar/learning),不夸大。
3. **联系方式占位符** `[手机号]`/`[邮箱]` 投递前必须替换为真实值;不进版本库的应使用 `.gitignore` 忽略 `data/cv/cv-real.md`。
4. **针对岗位微调**:同一份模板可生成多份派生简历(运维版/IoT版/AI版),只改"求职意向"和"项目排序"。

## 派生文件位置

| 文件 | 内容 | 是否进版本库 |
|------|------|------------|
| `templates/cv-template.md` | 本文件,纯模板 | ✅ 是 |
| `data/cv/cv-real.md` | 填好真实信息的完整简历 | ❌ 否(含个人隐私) |
| `data/cv/cv-{role}.md` | 针对岗位微调的派生版 | ❌ 否 |

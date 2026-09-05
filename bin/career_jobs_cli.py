import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
try:
    from career_os_store import add_timeline_event, get_db
except ModuleNotFoundError:
    from bin.career_os_store import add_timeline_event, get_db

# 确保 Windows 终端 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def list_jobs():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT j.id, j.company_name, j.job_title, j.category, j.city, j.salary_text, j.match_level, j.status
        FROM jobs j
        ORDER BY j.priority ASC, j.id ASC
    """)
    rows = c.fetchall()
    conn.close()

    print("\n" + "="*110)
    print(f"💼 【2027届校招精选与高价值擦边岗位全景清单】 (共收录 {len(rows)} 个岗位)")
    print("="*110)
    print(f"{'ID':<4} | {'企业名称':<25} | {'岗位名称':<32} | {'类别':<10} | {'城市':<16} | {'薪资待遇':<15} | {'匹配度':<10} | {'状态'}")
    print("-" * 110)
    for r in rows:
        jid, cname, title, cat, city, sal, match, status = r
        print(f"{jid:<4} | {cname[:23]:<25} | {title[:30]:<32} | {cat:<10} | {city[:14]:<16} | {sal:<15} | {match:<10} | {status}")
    print("="*110)
    print("💡 使用 'python career_jobs_cli.py detail <ID>' 查看岗位详情与投递直达链接")
    print("💡 使用 'python career_jobs_cli.py guide <ID/企业名>' 查看该企业真实面试画像与高频真题")
    print("💡 使用 'python career_jobs_cli.py apply <ID>' 标记为已投递并加入进度追踪管线")
    print("💡 使用 'python bin/career_jobs_cli.py exam [job_id] [--limit N] [--minutes N] [--seed N] [--all]' 启动线上机考并保存答题报告")
    print("💡 使用 'python bin/career_jobs_cli.py personality [job_id] [--full|--kind quick|full]' 启动职业性格/工作风格测评")
    print("💡 使用 'python bin/career_jobs_cli.py code-sandbox <ID> --trusted-local' 或启用 Judge0 插件判题")
    print("💡 使用 'python bin/career_jobs_cli.py interview <ID/企业名> [job_id]' 启动动态模拟面试 Agent")
    print("💡 使用 'python career_jobs_cli.py plugins' 查看可插拔开源适配器")
    print("💡 使用 'python bin/career_jobs_cli.py assessment-intel [企业名]' 查询官方/社区测评情报")
    print("💡 使用 'python bin/career_jobs_cli.py assessment-intel --job <ID>' 根据当前 JD 生成岗位测评准备画像")
    print("💡 使用 'python bin/career_jobs_cli.py project-candidates search --job <ID> --live' 搜索 JD 匹配的 GitHub 项目候选")
    print("💡 候选确认后再用 project-candidates apply <提案ID> --confirm 写入简历草稿")
    print("💡 使用 'python career_jobs_cli.py track' 查看求职全流程看板\n")

def show_job_detail(job_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT j.id, j.company_name, j.job_title, j.category, j.city, j.salary_text, j.education_req, 
               j.english_req, j.match_level, j.responsibilities, j.requirements, j.matching_analysis, 
               j.application_url, j.status, c.website, c.campus_url, c.welfare_summary
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.id = ?
    """, (job_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        print(f"❌ 未找到 ID 为 {job_id} 的岗位")
        return

    (jid, cname, title, cat, city, sal, edu, eng, match, resp, req, analysis, app_url, status, web, campus, welfare) = row

    print("\n" + "="*90)
    print(f"🎯 【岗位详情与匹配度分析】: {cname} - {title} (ID: {jid})")
    print("="*90)
    print(f"🏢 目标企业: {cname} ({web})")
    print(f"📍 工作地点: {city} | 薪资: {sal} | 学历: {edu} | 英语: {eng}")
    print(f"🌟 契合评级: {match} | 当前状态: 【{status}】")
    print(f"🎁 企业福利: {welfare}")
    print(f"🔗 校招网申直达: {app_url or campus}")
    print("-" * 90)
    print("📋 【核心职责】:\n" + (resp or "暂无详细描述"))
    print("\n📝 【任职要求】:\n" + (req or "暂无详细要求"))
    print("\n💡 【高价值匹配度分析与破局思路】:\n" + (analysis or "暂无分析"))
    print("="*90 + "\n")

def show_interview_guide(target):
    conn = get_db()
    c = conn.cursor()
    if str(target).isdigit():
        c.execute("""
            SELECT c.id, c.name, g.recruitment_process, g.resume_criteria, g.interview_rounds, g.typical_questions, g.score_weights, g.avoid_pitfalls, g.authentic_sources
            FROM companies c
            LEFT JOIN company_interview_guides g ON c.id = g.company_id
            WHERE c.id = ?
        """, (int(target),))
    else:
        c.execute("""
            SELECT c.id, c.name, g.recruitment_process, g.resume_criteria, g.interview_rounds, g.typical_questions, g.score_weights, g.avoid_pitfalls, g.authentic_sources
            FROM companies c
            LEFT JOIN company_interview_guides g ON c.id = g.company_id
            WHERE c.name LIKE ? OR c.alias LIKE ?
        """, (f"%{target}%", f"%{target}%"))
    
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"❌ 未找到匹配的企业面试指南: '{target}'")
        return

    for r in rows:
        cid, cname, process, criteria, rounds, questions, weights, pitfalls, sources = r
        print("\n" + "="*90)
        print(f"🎯 【{cname} · 校招全景通关与面试真题指南】 (企业 ID: {cid})")
        print("="*90)
        print("🚀 【官方真实校招流程】:\n  " + (process or "常规网申 -> 测评 -> 一面 -> 二面 -> Offer"))
        print("\n📄 【简历初筛与加分红线】:\n  " + (criteria or "工科背景，具备真实项目实战与动手能力。"))
        print("\n👥 【面试轮次与真实风格】:\n  " + (rounds or "技术一面 (基础+项目) -> 综合二面 (深挖与抗压) -> HR面"))
        print("\n🔥 【核心高频必考真题库】:\n" + (questions or "暂无收录真题"))
        print("\n⚖️ 【考官评分权重】:\n  " + (weights or "技术深度 (40%) > 逻辑表达 (35%) > 稳定性 (25%)"))
        print("\n⚠️ 【避坑指南】:\n  " + (pitfalls or "注意回答结构化，避免长篇大论。"))
        print("\n🔍 【真实信源】:\n  " + (sources or "企业校招公文与真实面经"))
        print("="*90 + "\n")

def track_pipeline():
    """查看求职全流程管线看板"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT j.status, COUNT(j.id)
        FROM jobs j
        GROUP BY j.status
    """)
    status_counts = dict(c.fetchall())

    c.execute("""
        SELECT j.id, j.company_name, j.job_title, j.city, j.salary_text, j.status
        FROM jobs j
        WHERE j.status != '待投递'
        ORDER BY j.updated_at DESC
    """)
    active_rows = c.fetchall()
    conn.close()

    print("\n" + "="*85)
    print("📊 【2027 届校招全流程动态追踪管线 (Pipeline Tracker)】")
    print("="*85)
    print(f"📌 待投递: {status_counts.get('待投递', 0)} | 🚀 已投递: {status_counts.get('已投递', 0)} | 📝 待笔试: {status_counts.get('待笔试', 0)} | 🎙️ 面试中: {status_counts.get('面试中', 0)} | 🏆 Offer: {status_counts.get('Offer', 0)}")
    print("-" * 85)
    if not active_rows:
        print("💡 当前所有 60 个岗位均为【待投递】就绪状态。使用 'python career_jobs_cli.py apply <ID>' 标记投递！")
    else:
        for r in active_rows:
            print(f"  • [ID: {r[0]}] {r[1]} - {r[2]} ({r[3]}) | 状态: 【{r[5]}】")
    print("="*85 + "\n")

def mark_apply(job_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT company_name, job_title FROM jobs WHERE id = ?", (job_id,))
    job = c.fetchone()
    if not job:
        conn.close()
        print(f"❌ 未找到岗位 ID {job_id}")
        return
    c.execute("UPDATE jobs SET status = '已投递', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
    add_timeline_event(conn, job_id=int(job_id), company_name=job[0], job_title=job[1],
                       event_type="已投递", notes="通过 Career OS CLI 标记")
    conn.commit()
    conn.close()
    print(f"\n✅ 岗位 ID {job_id} 已成功标记为【已投递】并加入动态追踪管线！")
    track_pipeline()

def show_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM companies")
    total_companies = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM company_interview_guides")
    total_guides = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mock_questions")
    total_questions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality'")
    personality_questions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND source_plugin LIKE 'github-%'")
    github_questions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND assessment_kind = 'career-personality-v1'")
    quick_personality_questions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mock_questions WHERE question_type = 'personality' AND assessment_kind = 'career-personality-ipip-neo-120'")
    full_personality_questions = c.fetchone()[0]
    source_counts = c.execute(
        "SELECT COALESCE(NULLIF(source_plugin, ''), 'legacy/未标注') AS source, COUNT(*) FROM mock_questions GROUP BY source ORDER BY COUNT(*) DESC, source"
    ).fetchall()
    conn.close()

    print("\n" + "="*60)
    print("📊 【Career OS 求职全景资产大盘统计】")
    print("="*60)
    print(f"🏢 目标企业总数: {total_companies} 家 (100% 连通)")
    print(f"💼 精选对口岗位: {total_jobs} 个")
    print(f"📚 逐一面试指南: {total_guides} 份 (100% 覆盖)")
    print(f"🎯 笔试与沙箱题: {total_questions} 题 (客观题 + 手撕代码 + 性格题)")
    print(f"🧭 职业性格/工作风格题: {personality_questions} 题")
    print(f"  ├─ 快速模式: {quick_personality_questions} 题")
    print(f"  ├─ IPIP-NEO-120 完整模式: {full_personality_questions} 题")
    print(f"  └─ GitHub 来源合计: {github_questions} 题")
    print("📦 题库来源分布:")
    for source, count in source_counts:
        print(f"  ├─ {source}: {count} 题")
    print("="*60 + "\n")


def show_assessment_intelligence(target=None):
    """查询企业官方/社区测评情报，不把历史帖子伪装成当前题库。"""

    path = Path(__file__).resolve().parents[1] / "data" / "assessment-intelligence.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ 测评情报文件无法读取: {exc}")
        return

    records = payload.get("records", [])
    if target:
        keyword = str(target).casefold()
        records = [
            item for item in records
            if keyword in str(item.get("company", "")).casefold()
            or keyword in str(item.get("scope", "")).casefold()
        ]
    if not records:
        print(f"❌ 没有匹配的测评情报: {target or '全部'}")
        return

    print("\n" + "=" * 96)
    print("🧭 【企业/社区秋招测评情报】")
    print("官方记录确认流程；社区记录仅作历史信号，正式题目以企业邮件为准。")
    print("=" * 96)
    for item in records:
        evidence = item.get("evidence_level", "unknown")
        source_type = item.get("source_type", "unknown")
        print(f"\n🏢 {item.get('company', '未知企业')} | {item.get('scope', '范围未注明')}")
        print(f"  证据: {evidence} / {source_type} | 年份: {item.get('reported_year', '未注明')}")
        print(f"  阶段: {item.get('assessment_stage', '未注明')}")
        print(f"  形式: {'、'.join(item.get('assessment_forms', [])) or '未公开'}")
        print(f"  题型: {'、'.join(item.get('question_families', [])) or '未公开'}")
        if item.get("duration"):
            print(f"  时长: {item['duration']}")
        print(f"  来源: {item.get('source_url', '')}")
        print(f"  边界: {item.get('notes', '')}")
    print("=" * 96 + "\n")


def show_job_assessment_profile(job_id):
    """根据 SQLite 中的当前 JD 生成岗位级测评准备建议。"""

    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        print(f"❌ job_id 必须是数字: {job_id}")
        return
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, company_name, job_title, category, responsibilities, requirements, english_req
        FROM jobs WHERE id = ?
        """,
        (job_id,),
    ).fetchone()
    conn.close()
    if not row:
        print(f"❌ 未找到岗位 ID {job_id}")
        return

    try:
        from jd_assessment_mapper import infer_assessment_profile
    except ModuleNotFoundError:
        from bin.jd_assessment_mapper import infer_assessment_profile
    profile = infer_assessment_profile(row)
    print("\n" + "=" * 96)
    print(f"🎯 【JD 对应测评准备画像】岗位 {profile['job_id']} · {profile['company_name']} · {profile['job_title']}")
    print(f"类别: {profile['category']}")
    print("说明: 以下是基于当前 JD 的可解释推导，不是企业已确认的题库。")
    print("=" * 96)
    print(f"命中信号: {', '.join(profile['matched_signals'])}")
    print(f"建议题型: {'、'.join(profile['question_families'])}")
    print(f"建议训练: {'、'.join(profile['practice'])}")
    for track in profile["tracks"]:
        print(f"\n[{track['label']}]")
        print(f"  题型: {'、'.join(track['question_families'])}")
        print(f"  训练: {'、'.join(track['practice'])}")
    print("=" * 96 + "\n")


def show_all_job_assessment_summary():
    """汇总当前 jobs 表的 JD 测评轨道覆盖情况。"""

    try:
        from jd_assessment_mapper import profiles_for_jobs, summarize_profiles
    except ModuleNotFoundError:
        from bin.jd_assessment_mapper import profiles_for_jobs, summarize_profiles
    conn = get_db()
    rows = conn.execute(
        "SELECT id, company_name, job_title, category, responsibilities, requirements, english_req FROM jobs"
    ).fetchall()
    conn.close()
    profiles = profiles_for_jobs(rows)
    counts = summarize_profiles(profiles)
    print("\n" + "=" * 72)
    print("🗺️ 【当前数据库 JD → 测评轨道覆盖】")
    print(f"已分析岗位: {len(profiles)} 个；规则仅依据 JD 字段推导，不代表企业官方题库。")
    print("=" * 72)
    for track_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {track_id:<24} {count:>3} 个岗位")
    print("\n查看单个岗位: python bin/career_jobs_cli.py assessment-intel --job <ID>")
    print("=" * 72 + "\n")


def _flag_value(args, flag: str, default=None):
    if flag not in args:
        return default
    pos = args.index(flag)
    return args[pos + 1] if pos + 1 < len(args) else default


def project_candidates_command(args):
    """管理 JD 驱动的 GitHub 项目候选库和人工确认提案。"""

    try:
        from github_project_candidates import (
            GitHubRestSource,
            apply_proposal,
            build_search_queries,
            candidate_rows,
            confirm_candidate,
            get_job,
            save_candidates,
        )
    except ModuleNotFoundError:
        from bin.github_project_candidates import (
            GitHubRestSource,
            apply_proposal,
            build_search_queries,
            candidate_rows,
            confirm_candidate,
            get_job,
            save_candidates,
        )

    subcommand = args[0].lower() if args else "list"
    if subcommand == "search":
        raw_job = _flag_value(args, "--job")
        if not raw_job or not str(raw_job).isdigit():
            print("❌ project-candidates search 需要 --job <岗位ID>")
            return
        limit = _flag_value(args, "--limit", "10")
        try:
            limit = max(1, min(int(limit), 30))
        except ValueError:
            print("❌ --limit 必须是 1-30 的整数")
            return
        conn = get_db()
        try:
            job = get_job(conn, int(raw_job))
            queries = build_search_queries(job)
            print(f"🎯 {job['company_name']} · {job['job_title']} (岗位 {raw_job})")
            print("🔎 JD → GitHub 查询：")
            for query in queries:
                print(f"  - {query}")
            if "--live" not in args:
                print("👀 当前为查询预览；加 --live 才会访问 GitHub 并写入候选库")
                return
            preferred = _flag_value(args, "--provider")
            source = None
            try:
                from career_os_plugins import get_plugin_manager
            except ModuleNotFoundError:
                from bin.career_os_plugins import get_plugin_manager
            if preferred or os.environ.get("CAREER_OS_PLUGINS", "").strip():
                source = get_plugin_manager().capability("project_source", preferred=preferred)
            if source is None:
                source = GitHubRestSource()
            all_rows = []
            for query in queries:
                rows = source.search(query, limit=limit)
                all_rows.extend((query, row) for row in rows)
            if all_rows:
                conn.execute(
                    "UPDATE github_project_candidates SET status='stale', updated_at=? "
                    "WHERE job_id=? AND provider=? AND status='candidate'",
                    (datetime.now(timezone.utc).isoformat(timespec="seconds"), int(raw_job), source.provider_name),
                )
            total = 0
            for query, row in all_rows:
                total += save_candidates(conn, job_id=int(raw_job), query=query, source=source, candidates=[row])
            print(f"✅ 已保存/更新 {total} 条候选（provider={source.provider_name}）；默认仍需人工确认")
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"❌ 项目候选搜索失败: {exc}")
        finally:
            conn.close()
        return

    if subcommand == "list":
        raw_job = _flag_value(args, "--job")
        job_id = int(raw_job) if raw_job and str(raw_job).isdigit() else None
        status = _flag_value(args, "--status", "candidate")
        if status == "all":
            status = None
        conn = get_db()
        try:
            rows = candidate_rows(conn, job_id=job_id, status=status)
            if not rows:
                print("📭 暂无候选；先运行 project-candidates search --job <ID> --live")
                return
            print("\n📦 【GitHub 项目候选库】")
            for row in rows:
                print(
                    f"  [{row['id']}] 岗位{row['job_id']} {row['repo_full_name']} "
                    f"score={row['relevance_score']:.2f} ★{row['stars']} "
                    f"license={row['license_spdx'] or 'unknown'}({row['license_status']}) status={row['status']}\n"
                    f"      {row['repo_url']} | 匹配: {', '.join(json.loads(row['matched_terms_json'] or '[]')) or '待复核'}"
                )
        finally:
            conn.close()
        return

    if subcommand == "confirm":
        raw_id = args[1] if len(args) > 1 and args[1].isdigit() else _flag_value(args, "--candidate")
        resume_key = _flag_value(args, "--resume")
        evidence = _flag_value(args, "--evidence", "")
        claim_level = _flag_value(args, "--claim-level", "reference")
        if not raw_id or not str(raw_id).isdigit() or not resume_key:
            print("❌ confirm 用法: project-candidates confirm <候选ID> --resume cv-ops --evidence \"个人证据/参考说明\" --claim-level reference|adapted|implemented --confirm")
            return
        conn = get_db()
        try:
            proposal = confirm_candidate(
                conn,
                candidate_id=int(raw_id),
                resume_key=resume_key,
                evidence=evidence,
                claim_level=claim_level,
                confirm="--confirm" in args,
            )
            print(f"✅ 已人工确认候选 {raw_id}，提案 ID={proposal['id']}；尚未写入简历")
            print("   下一步：project-candidates apply <提案ID> --confirm")
        except (ValueError, FileNotFoundError, OSError) as exc:
            print(f"❌ 候选确认失败: {exc}")
        finally:
            conn.close()
        return

    if subcommand == "apply":
        raw_id = args[1] if len(args) > 1 and args[1].isdigit() else _flag_value(args, "--proposal")
        if not raw_id or not str(raw_id).isdigit():
            print("❌ apply 用法: project-candidates apply <提案ID> --confirm")
            return
        conn = get_db()
        try:
            path = apply_proposal(conn, proposal_id=int(raw_id), confirm="--confirm" in args)
            print(f"✅ 已将人工确认提案写入简历草稿: {path}")
        except (ValueError, FileNotFoundError, OSError) as exc:
            print(f"❌ 写入简历失败: {exc}")
        finally:
            conn.close()
        return

    if subcommand == "proposals":
        conn = get_db()
        try:
            rows = conn.execute(
                """
                SELECT p.id, p.resume_key, p.claim_level, p.status, p.candidate_id,
                       c.repo_full_name, p.updated_at
                FROM resume_project_proposals p
                JOIN github_project_candidates c ON c.id=p.candidate_id
                ORDER BY p.id DESC
                """
            ).fetchall()
            if not rows:
                print("📭 暂无简历提案")
                return
            for row in rows:
                print(f"  提案 {row['id']} | {row['repo_full_name']} -> {row['resume_key']} | {row['claim_level']} | {row['status']} | {row['updated_at']}")
        finally:
            conn.close()
        return

    print("❌ 支持: search, list, confirm, apply, proposals")

def main():
    if len(sys.argv) < 2:
        list_jobs()
        return

    cmd = sys.argv[1].lower()
    if cmd == 'list':
        list_jobs()
    elif cmd == 'detail' and len(sys.argv) > 2:
        show_job_detail(sys.argv[2])
    elif cmd == 'guide' and len(sys.argv) > 2:
        show_interview_guide(sys.argv[2])
    elif cmd == 'track':
        track_pipeline()
    elif cmd == 'apply' and len(sys.argv) > 2:
        mark_apply(sys.argv[2])
    elif cmd == 'stats':
        show_stats()
    elif cmd in {'assessment-intel', 'assessment-intelligence'}:
        args = sys.argv[2:]
        if args and args[0].lower() in {'--job', 'job'}:
            show_job_assessment_profile(args[1] if len(args) > 1 else None)
        elif args and args[0].lower() in {'--all-jobs', 'all'}:
            show_all_job_assessment_summary()
        else:
            show_assessment_intelligence(' '.join(args) if args else None)
    elif cmd == 'project-candidates':
        project_candidates_command(sys.argv[2:])
    elif cmd == 'plugins':
        from career_os_plugins import get_plugin_manager
        manager = get_plugin_manager()
        active = manager.enabled_ids()
        print("\n🔌 Career OS 可插拔适配器")
        for manifest in manager.discover():
            state = '启用' if manifest.plugin_id in active else '关闭'
            print(f"  [{state}] {manifest.plugin_id} v{manifest.version} | {', '.join(manifest.capabilities)} | {manifest.name}")
        print("  启用方式: $env:CAREER_OS_PLUGINS='judge0,exameow,openai-compatible-interview'")
    elif cmd == 'import-questions' and len(sys.argv) > 2:
        from question_bank_adapter import QuestionBankAdapter
        source_plugin = 'external'
        if '--source' in sys.argv:
            pos = sys.argv.index('--source')
            source_plugin = sys.argv[pos + 1] if pos + 1 < len(sys.argv) else source_plugin
        apply_import = '--apply' in sys.argv[3:]
        count = QuestionBankAdapter().load(sys.argv[2], source_plugin=source_plugin, apply=apply_import)
        print((f"✅ 已导入/更新 {count} 道题，来源插件: {source_plugin}" if apply_import
               else f"👀 题库导入预览: {count} 道题；加 --apply 才写入"))
    elif cmd == 'import-jobs' and len(sys.argv) > 2:
        from job_source_adapter import JobSourceAdapter
        source_plugin = 'external'
        if '--source' in sys.argv:
            pos = sys.argv.index('--source')
            source_plugin = sys.argv[pos + 1] if pos + 1 < len(sys.argv) else source_plugin
        apply_import = '--apply' in sys.argv[3:]
        result = JobSourceAdapter().load(sys.argv[2], source_plugin=source_plugin, apply=apply_import)
        if apply_import:
            print(f"✅ 岗位导入完成: 新增 {result['inserted']}，更新 {result['updated']}，企业 {result['companies']} 家")
        else:
            print(f"👀 岗位导入预览: {result['preview']} 条 / {result['companies']} 家；加 --apply 才写入")
    elif cmd == 'exam':
        from mock_oa_sandbox import run_choice_quiz
        args = sys.argv[2:]
        job_id = int(args[0]) if args and args[0].isdigit() else None
        if job_id is not None:
            args = args[1:]
        limit = None if '--all' in args else 30
        duration_minutes = 30
        seed = None
        for flag, target in (('--limit', 'limit'), ('--minutes', 'duration_minutes'), ('--seed', 'seed')):
            if flag in args:
                pos = args.index(flag)
                if pos + 1 >= len(args):
                    print(f"❌ {flag} 需要一个整数参数")
                    return
                try:
                    value = int(args[pos + 1])
                except ValueError:
                    print(f"❌ {flag} 需要一个整数参数")
                    return
                if target == 'limit':
                    limit = value
                elif target == 'duration_minutes':
                    duration_minutes = value
                else:
                    seed = value
        run_choice_quiz(job_id=job_id, limit=limit, duration_minutes=duration_minutes, seed=seed)
    elif cmd in {'personality', 'personality-test', 'work-style'}:
        try:
            from personality_assessment import run_personality_assessment
        except ModuleNotFoundError:
            from bin.personality_assessment import run_personality_assessment
        args = sys.argv[2:]
        job_id = int(args[0]) if args and args[0].isdigit() else None
        if job_id is not None:
            args = args[1:]
        assessment_kind = None
        if '--full' in args:
            assessment_kind = 'career-personality-ipip-neo-120'
        if '--kind' in args:
            pos = args.index('--kind')
            if pos + 1 >= len(args):
                print("❌ --kind 需要 quick 或 full")
                return
            assessment_kind = args[pos + 1]
        if '--assessment-kind' in args:
            pos = args.index('--assessment-kind')
            if pos + 1 >= len(args):
                print("❌ --assessment-kind 需要题库 assessment_kind")
                return
            assessment_kind = args[pos + 1]
        if assessment_kind in {'quick', 'career-personality-v1'}:
            assessment_kind = 'career-personality-v1'
        elif assessment_kind in {'full', 'career-personality-ipip-neo-120'}:
            assessment_kind = 'career-personality-ipip-neo-120'
        elif assessment_kind:
            print(f"❌ 不支持的性格测评模式: {assessment_kind}")
            return
        kwargs = {'job_id': job_id}
        if assessment_kind:
            kwargs['assessment_kind'] = assessment_kind
        run_personality_assessment(**kwargs)
    elif cmd == 'code-sandbox':
        qid = int(sys.argv[2]) if len(sys.argv) > 2 else 11
        from mock_oa_sandbox import run_code_sandbox
        trusted = '--trusted-local' in sys.argv[3:]
        job_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
        run_code_sandbox(qid, trusted_local=trusted, job_id=job_id)
    elif cmd == 'interview':
        target = sys.argv[2] if len(sys.argv) > 2 else "36"
        from mock_interview_agent import run_mock_interview
        job_id = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
        run_mock_interview(target, job_id=job_id)
    else:
        print(f"❌ 未知命令: {cmd}")
        print("💡 支持命令: list, detail <ID>, guide <ID/Name>, track, apply <ID>, project-candidates search|list|confirm|apply|proposals, exam [job_id] [--limit N] [--minutes N] [--seed N] [--all], personality [job_id] [--full|--kind quick|full], assessment-intel [企业名|--job <ID>|--all-jobs], code-sandbox <ID> [--trusted-local], interview <ID> [job_id], plugins, import-questions <file> --source <plugin>, import-jobs <file> [--source <plugin>] [--apply], stats")

if __name__ == "__main__":
    main()

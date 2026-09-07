"""岗位搜寻截图管道：模拟真人浏览招聘渠道，把页面截图落盘。

定位：只负责「浏览 + 截图 + 留痕」，不做任何 DOM 解析或接口爬取。
结构化提取由 LLM 读截图完成（load 模式），提取结果经
scripts/job_discovery_import.py 写入 platform_recruitment_leads 表。

用法：
    python scripts/job_discovery_screenshot.py --channel guopin --pages 2
    python scripts/job_discovery_screenshot.py --channel boss          # 首次自动弹窗扫码
    python scripts/job_discovery_screenshot.py --channel boss --no-detail  # 跳过详情页

产物：
    data/job_discovery/screenshots/<channel>/<日期>/p<页>-s<屏>.png   列表页
    data/job_discovery/screenshots/<channel>/<日期>/d<页>-<序>.png    岗位详情页(JD)
    data/job_discovery/manifests/<channel>-<日期>-<时分>.json

反算法搜索策略（来源：社区实践 + get_jobs/jobclaw 源码调研）：
    - 多关键词交叉轮换，覆盖算法的岗位池盲区
    - 详情页全页截图包含 HR 活跃时间区域，供提取阶段过滤僵尸岗
    - PC 网页端岗位池与 APP 不互通，本管道即 PC 侧补盲
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "job_discovery_channels.yml"
OUT_ROOT = ROOT / "data" / "job_discovery"

sys.path.insert(0, str(ROOT / "bin"))


def _human_pause(low: float = 1.2, high: float = 3.5) -> None:
    """模拟真人阅读停顿，节奏随机，避免机械等间隔。"""
    time.sleep(random.uniform(low, high))


def _human_scroll(page, steps: int) -> None:
    """逐屏随机滚动：随机距离 + 随机间隔，触发懒加载（渐进滚动，不瞬移）。"""
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(350, 650))
        _human_pause(0.8, 2.2)


def _wait_for_login(page, channel: dict, timeout_s: int = 180) -> bool:
    """轮询登录态，代替固定等待。

    判定依据（渠道可配 login_detect_selector，默认 BOSS 的头像入口）：
      - login_detect_selector 出现 = 已登录
      - 超时未出现 = 放弃本轮（cookie 已留存在 profile，下次续扫）
    """
    detect = channel.get("login_detect_selector", "//li[@class='nav-figure']")
    print(f"[{channel['id']}] 请在弹出的浏览器中完成登录/扫码（最长 {timeout_s}s），本窗口每 3s 自动检测...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if page.locator(detect).count() > 0:
                print(f"[{channel['id']}] 登录态确认 ✓")
                return True
        except Exception:
            pass
        time.sleep(3)
    print(f"[{channel['id']}] 等待登录超时，退出本轮（登录进度已保存在浏览器 profile）")
    return False


def _shoot_details(context, page, channel: dict, kw: str, page_no: int,
                   shot_dir: Path, entries: list, max_details: int) -> None:
    """从列表页逐个点开岗位详情页截图（新标签页打开 = 真人 Ctrl+click 习惯）。

    两种模式（渠道二选一配置）：
      - detail_link_selector: 卡片带 href，读链接后新开标签页直达（BOSS/智联）
      - detail_click_selector: SPA 无 href，直接点击卡片等弹出新标签（国聘）
    详情页全页截图天然包含 JD 全文和 HR 活跃时间，供提取阶段过滤僵尸岗。
    """
    click_sel = channel.get("detail_click_selector")
    link_sel = channel.get("detail_link_selector")
    if max_details <= 0 or not (click_sel or link_sel):
        return

    if click_sel:
        # 点击模式：SPA 站点，卡片点击后 window.open 新标签
        try:
            cards = page.locator(click_sel)
            count = min(cards.count(), max_details)
        except Exception as exc:
            print(f"[{channel['id']}/click] 卡片定位失败，跳过详情阶段: {exc}")
            return
        for idx in range(count):
            detail = None
            try:
                # 每次重查 locator（翻页/滚动后 DOM 会变）， nth(idx) 保持顺序
                with context.expect_page(timeout=10_000) as popup_info:
                    page.locator(click_sel).nth(idx).click()
                detail = popup_info.value
                detail.wait_for_load_state("domcontentloaded", timeout=30_000)
                _human_pause(2.0, 4.0)
                _human_scroll(detail, 3)
                shot_path = shot_dir / f"d{page_no:02d}-{kw.replace(' ', '_')}-{idx + 1:02d}.png"
                detail.screenshot(path=str(shot_path), full_page=True)
                entries.append(
                    {
                        "channel": channel["id"],
                        "channel_name": channel.get("name", channel["id"]),
                        "keyword": kw,
                        "page": page_no,
                        "detail_index": idx + 1,
                        "detail_url": detail.url,
                        "screenshot_path": str(shot_path.relative_to(ROOT)),
                        "screenshot_type": "detail",
                        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    }
                )
                print(f"[{channel['id']}] 详情已截图: {shot_path.name}")
            except Exception as exc:
                print(f"[{channel['id']}] 详情页失败(第{idx + 1}个): {exc}")
                # 点击后可能原地跳转而非新标签，回退到列表页继续
                try:
                    if page.url != entries[-1].get("page_url", "") if entries else False:
                        page.go_back(timeout=15_000)
                        _human_pause(1.5, 2.5)
                except Exception:
                    pass
            finally:
                if detail:
                    detail.close()
                _human_pause(1.5, 3.0)  # 详情之间留间隔，避免连点被风控
        return

    # href 模式
    try:
        links = page.locator(link_sel)
        count = min(links.count(), max_details)
    except Exception as exc:
        print(f"[{channel['id']}] 详情链接定位失败，跳过详情阶段: {exc}")
        return

    for idx in range(count):
        href = links.nth(idx).get_attribute("href")
        if not href:
            continue
        url = href if href.startswith("http") else (
            channel.get("detail_url_base", page.url.split("?")[0].rstrip("/") + "/") + href.lstrip("/")
        )
        # BOSS 详情链接是相对路径 /job_detail/xxx.html，统一拼主域
        if not href.startswith("http") and "job_detail" in href:
            url = "https://www.zhipin.com" + href
        detail = context.new_page()
        try:
            detail.goto(url, wait_until="domcontentloaded", timeout=45_000)
            _human_pause(2.0, 4.0)
            _human_scroll(detail, 3)
            shot_path = shot_dir / f"d{page_no:02d}-{kw.replace(' ', '_')}-{idx + 1:02d}.png"
            detail.screenshot(path=str(shot_path), full_page=True)
            entries.append(
                {
                    "channel": channel["id"],
                    "channel_name": channel.get("name", channel["id"]),
                    "keyword": kw,
                    "page": page_no,
                    "detail_index": idx + 1,
                    "detail_url": url,
                    "screenshot_path": str(shot_path.relative_to(ROOT)),
                    "screenshot_type": "detail",
                    "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                }
            )
            print(f"[{channel['id']}] 详情已截图: {shot_path.name}")
        except Exception as exc:
            print(f"[{channel['id']}] 详情页失败({url[:60]}): {exc}")
        finally:
            detail.close()
            _human_pause(1.5, 3.0)  # 详情之间留间隔，避免连点被风控


def _shoot_channel(channel: dict, pages: int, scroll_steps: int, keyword: str,
                   max_details: int) -> list[dict]:
    """打开单渠道，浏览 + 截图（列表页 + 详情页），返回 manifest 条目。"""
    now = datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    shot_dir = OUT_ROOT / "screenshots" / channel["id"] / date_dir
    shot_dir.mkdir(parents=True, exist_ok=True)

    needs_login = channel.get("needs_login", False)
    headless = channel.get("headless", True) and not needs_login
    entries: list[dict] = []

    with sync_playwright() as p:
        # 持久化会话：cookie 存本地，登录类渠道一次扫码多日免登
        profile_dir = OUT_ROOT / "browser_profiles" / channel["id"]
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": random.choice([1366, 1440, 1536]), "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        # 登录渠道：先探已有 cookie 是否还有效，失效才弹扫码等待
        if needs_login:
            page.goto(channel["entry_url"], wait_until="domcontentloaded", timeout=60_000)
            _human_pause(2.0, 3.0)
            detect = channel.get("login_detect_selector", "//li[@class='nav-figure']")
            if page.locator(detect).count() == 0 and not _wait_for_login(page, channel):
                context.close()
                return entries

        keywords = channel.get("keywords") or [keyword]
        for kw in keywords:
            search_url = channel.get("search_url_template")
            if search_url:
                page.goto(search_url.format(kw=kw), wait_until="domcontentloaded", timeout=60_000)
            else:
                page.goto(channel["entry_url"], wait_until="domcontentloaded", timeout=60_000)
                sel = channel.get("search_input_selector")
                if sel:
                    page.fill(sel, kw)
                    page.keyboard.press("Enter")
            _human_pause(2.5, 5.0)

            for page_no in range(1, pages + 1):
                _human_scroll(page, scroll_steps)
                shot_path = shot_dir / f"p{page_no:02d}-{kw.replace(' ', '_')}.png"
                page.screenshot(path=str(shot_path), full_page=False)
                entries.append(
                    {
                        "channel": channel["id"],
                        "channel_name": channel.get("name", channel["id"]),
                        "keyword": kw,
                        "page": page_no,
                        "page_url": page.url,
                        "screenshot_path": str(shot_path.relative_to(ROOT)),
                        "screenshot_type": "list",
                        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    }
                )
                print(f"[{channel['id']}] 列表已截图: {shot_path.name}")

                # 详情页阶段：当前列表页的前 N 个岗位
                _shoot_details(context, page, channel, kw, page_no, shot_dir, entries, max_details)

                next_sel = channel.get("next_page_selector")
                if page_no < pages and next_sel:
                    try:
                        page.click(next_sel, timeout=5_000)
                        _human_pause(2.0, 4.0)
                    except Exception:
                        print(f"[{channel['id']}] 第 {page_no} 页后无下一页，提前结束")
                        break

        context.close()

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="模拟真人浏览招聘渠道并截图（列表+详情）")
    parser.add_argument("--channel", required=True, help="渠道 id（见 config/job_discovery_channels.yml）")
    parser.add_argument("--pages", type=int, default=None, help="覆盖配置里的 pages")
    parser.add_argument("--keyword", default=None, help="覆盖/追加搜索关键词")
    parser.add_argument("--max-details", type=int, default=5, help="每个列表页最多截几个岗位详情")
    parser.add_argument("--no-detail", action="store_true", help="跳过详情页阶段")
    parser.add_argument("--login-timeout", type=int, default=180, help="扫码等待秒数")
    args = parser.parse_args()

    channels = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    defaults = channels.get("defaults", {})
    target = next((c for c in channels["channels"] if c["id"] == args.channel), None)
    if target is None:
        print(f"未知渠道: {args.channel}；可用: {[c['id'] for c in channels['channels']]}")
        return 1

    pages = args.pages or int(defaults.get("pages", 2))
    scroll_steps = int(defaults.get("scroll_steps", 5))
    keyword = args.keyword or str(defaults.get("keyword", ""))
    max_details = 0 if args.no_detail else args.max_details
    target["login_timeout"] = args.login_timeout

    entries = _shoot_channel(target, pages, scroll_steps, keyword, max_details)

    manifest_dir = OUT_ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    manifest_path = manifest_dir / f"{target['id']}-{stamp}.json"
    manifest_path.write_text(
        json.dumps({"channel": target["id"], "entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lists = sum(1 for e in entries if e["screenshot_type"] == "list")
    details = sum(1 for e in entries if e["screenshot_type"] == "detail")
    print(f"manifest: {manifest_path.relative_to(ROOT)}（列表 {lists} 张 + 详情 {details} 张）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""CET-4 真题 PDF -> Markdown 转换器（导库工具）。

依赖：`pip install pymupdf`

用法：
    python bin/cet4_pdf_import.py <pdf目录> <输出根目录> [--dry-run]

约定：
- 源 PDF 为 0609x/CET46-Resources 仓库的 cet4_YYYY_MM_N.pdf（含 KEYS 页为佳）。
- 输出到 <输出根目录>/YYYY.MM/cet4-YYYY-MM-N.md，样式对齐 2023.06/2023.12 既有试卷。
- 同行多选项（A)… C)…）按字母拆回 4 行；选词填空词库还原为 2 列表格。
- 卷末 KEYS 页会解析成 {题号: 字母}，用于写入 cet4-answers.json；无 KEYS 的卷（如 2026.06）答案留空。
- 仅对有文本层的 PDF 有效；扫描件（2020-2023 多数源卷）解析结果为空，需人工录入或 OCR。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz

CJK = re.compile(r"[\u4e00-\u9fff]")
PART_RE = re.compile(r"^Part\s+(I|II|III|IV)$")
SEC_RE = re.compile(r"^Section\s+([ABC])$")
PASSAGE_RE = re.compile(r"^Passage\s+(One|Two|Three)$")
GUIDE_RE = re.compile(r"^Questions\s+(\d+)\s+(and|to)\s+(\d+)\s+are based on")
QNUM_RE = re.compile(r"^(\d{1,2})\s*[.．]?\s*(?=[A-Z“(])")
OPT_INLINE = re.compile(r"(?<![A-Za-z0-9])([A-D])\)\s*")
BANK_INLINE = re.compile(r"(?<![A-Za-z0-9])([A-O])\)\s*")
BLANK_RE = re.compile(r"_{3,}\s*(\d{1,2})\s*_{3,}")
TITLE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")


def get_lines(pdf_path: Path):
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                if not text.strip():
                    continue
                fonts = " ".join(s["font"] for s in line["spans"])
                lines.append(
                    {
                        "text": text.strip(),
                        "x0": line["bbox"][0],
                        "y0": line["bbox"][1],
                        "italic": all(s["flags"] & 2 for s in line["spans"]),
                        "bold": "Bold" in fonts,
                    }
                )
        lines.sort(key=lambda l: (round(l["y0"], 1), l["x0"]))
        pages.append(lines)
    return pages


def split_options(text: str, pattern=OPT_INLINE):
    marks = list(pattern.finditer(text))
    out = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), text[start:end].strip()))
    return out


def parse_keys(lines):
    numbers, letters = {}, []
    for l in lines:
        t = l["text"].strip()
        if t.isdigit() and 1 <= int(t) <= 55:
            numbers[int(t)] = (l["y0"], l["x0"])
        elif re.fullmatch(r"[A-O]", t):
            letters.append((t, l["y0"], l["x0"]))
    keys = {}
    for num, (ny, nx) in numbers.items():
        best = None
        for lt, ly, lx in letters:
            if ly > ny and ly - ny < 30:
                dist = abs(lx - nx)
                if best is None or dist < best[0]:
                    best = (dist, lt)
        if best and best[0] < 12:
            keys[num] = best[1]
    return keys


class PaperParser:
    def __init__(self, pdf_path: Path):
        self.pages = get_lines(pdf_path)
        self.raw_title = None
        self.parts = []
        self.keys = {}
        self.bank = []
        self.part = None
        self.section = None
        self.question = None
        self.buf = []
        self.mode = None
        self.body_left = None
        self._parse()

    # ---------- block plumbing ----------
    def _ensure_part(self):
        if self.part is None:
            self.part = {"roman": None, "title": "", "minutes": "", "sections": []}
            self.parts.append(self.part)

    def _ensure_section(self, label):
        self._ensure_part()
        self.section = {"label": label, "blocks": [], "bank": []}
        self.part["sections"].append(self.section)
        self.body_left = None

    def _add(self, block):
        self._ensure_part()
        if self.section is None:
            self._ensure_section("")
        self.section["blocks"].append(block)

    def _flush(self):
        if self.buf:
            text = " ".join(self.buf).strip()
            text = re.sub(r"(?<=[\u4e00-\u9fff，。；：、“”（）]) +(?=[\u4e00-\u9fff，。；：、“”（）])", "", text)
            text = BLANK_RE.sub(lambda m: f"<u>&emsp;{m.group(1)}&emsp;</u>", text)
            self._add({"type": "para", "text": text})
            self.buf = []

    def _flush_question(self):
        if self.question is not None:
            self.question["options"].sort(key=lambda o: o["letter"])
            self._add(self.question)
            self.question = None

    # ---------- main loop ----------
    def _parse(self):
        for page in self.pages:
            if any(l["text"].strip() == "KEYS" for l in page[:4]):
                self._flush()
                self._flush_question()
                self.keys.update(parse_keys(page))
                continue

            i = 0
            while i < len(page):
                line = page[i]
                text = line["text"]

                # 页脚：试卷名 + 页码，以及紧邻的纯数字页码
                if self.raw_title is not None and re.search(r"(大学英语)?四级考试.*真题", text):
                    i += 1
                    continue
                if re.search(r"(真题|考试).*?\d{1,2}\s*$", text):
                    i += 1
                    continue
                if text.strip().isdigit() and int(text) <= 9:
                    i += 1
                    continue

                if self.raw_title is None and TITLE_RE.search(text) and (
                    "四级" in text or "真题" in text
                ):
                    self.raw_title = text
                    i += 1
                    continue

                m = PART_RE.match(text)
                if m:
                    self._flush()
                    self._flush_question()
                    row, j = [text], i + 1
                    while j < len(page) and abs(page[j]["y0"] - line["y0"]) < 4:
                        row.append(page[j]["text"])
                        j += 1
                    title, minutes = "", ""
                    for seg in row[1:]:
                        if seg.startswith("("):
                            minutes = seg.strip("() ")
                        else:
                            title = f"{title} {seg}".strip()
                    self.part = {"roman": m.group(1), "title": title, "minutes": minutes, "sections": []}
                    self.parts.append(self.part)
                    self.section = None
                    self.mode = None
                    self.body_left = None
                    i = j
                    continue

                m = SEC_RE.match(text)
                if m:
                    self._flush()
                    self._flush_question()
                    self._ensure_section(m.group(1))
                    self.mode = "passage" if self.part["roman"] == "III" else None
                    i += 1
                    continue

                if PASSAGE_RE.match(text):
                    self._flush()
                    self._flush_question()
                    self._add({"type": "passage_title", "text": text})
                    i += 1
                    continue

                m = GUIDE_RE.match(text)
                if m:
                    self._flush()
                    self._flush_question()
                    self._add({"type": "guide", "text": text})
                    self.mode = "passage"
                    i += 1
                    continue

                if text.startswith("Directions:"):
                    self._flush()
                    self._flush_question()
                    buf, j = [text], i + 1
                    # Directions 正文在源 PDF 中为斜体，据此精确收尾，避免吞掉后续文章
                    while j < len(page) and page[j]["italic"]:
                        buf.append(page[j]["text"])
                        j += 1
                    self._add({"type": "directions", "text": " ".join(buf)})
                    i = j
                    continue

                # 纯数字行：2026 版 PDF 的选词填空空格号
                if text.isdigit() and self.section is not None and self.section["label"] == "A" and self.part["roman"] == "III":
                    self.buf.append(f"<u>&emsp;{text}&emsp;</u>")
                    i += 1
                    continue

                if line["bold"] and line["x0"] > 110 and len(text) < 120 and not GUIDE_RE.match(text):
                    self._flush()
                    self._flush_question()
                    self._add({"type": "passage_title", "text": text})
                    self.mode = "passage"
                    i += 1
                    continue

                m = QNUM_RE.match(text)
                if m:
                    self._flush()
                    self._flush_question()
                    num = int(m.group(1))
                    opts = split_options(text)
                    if opts:
                        self.question = {
                            "type": "question",
                            "num": num,
                            "stem": "",
                            "options": [{"letter": a, "text": b} for a, b in opts],
                        }
                    else:
                        stem = re.sub(r"^\d{1,2}\s*[.．]?\s*", "", text).strip()
                        self.question = {"type": "question", "num": num, "stem": stem, "options": []}
                    i += 1
                    continue

                if re.match(r"^[A-D]\)\s*", text) and self.question is not None and len(self.question["options"]) < 4:
                    for a, b in split_options(text):
                        self.question["options"].append({"letter": a, "text": b})
                    i += 1
                    continue

                if (
                    re.match(r"^[A-O]\)\s*", text)
                    and self.section is not None
                    and self.section["label"] == "A"
                    and self.part["roman"] == "III"
                ):
                    for a, b in split_options(text, BANK_INLINE):
                        self.section["bank"].append((a, b))
                    i += 1
                    continue

                if (
                    re.match(r"^[A-O]\)", text)
                    and self.section is not None
                    and self.section["label"] == "B"
                    and self.part["roman"] == "III"
                ):
                    self._flush()
                    self._flush_question()
                    self._add({"type": "para_label", "text": text})
                    self.mode = "seb"
                    i += 1
                    continue

                # 段内续行
                if self.mode == "seb" and self.section is not None and self.section["label"] == "B":
                    last = self.section["blocks"][-1] if self.section["blocks"] else None
                    if last and last["type"] in ("para_label", "para"):
                        if last["type"] == "para_label":
                            last["type"] = "para"
                            last["text"] = f"{last['text']} {text}".strip()
                        else:
                            last["text"] = f"{last['text']} {text}".strip()
                        i += 1
                        continue

                if self.question is not None and not text.startswith(("Part", "Section", "Questions", "Passage")):
                    if self.question["options"]:
                        self.question["options"][-1]["text"] = (
                            self.question["options"][-1]["text"] + " " + text
                        ).strip()
                    else:
                        self.question["stem"] = (self.question["stem"] + " " + text).strip()
                    i += 1
                    continue

                if self.mode == "passage" and self.section is not None:
                    base = self.body_left if self.body_left is not None else line["x0"]
                    if line["x0"] < base:
                        self.body_left = line["x0"]
                    if self.buf and line["x0"] > base + 8:
                        self._flush()
                    self.buf.append(text)
                    i += 1
                    continue

                if self.part is not None and self.part["roman"] == "IV":
                    self.buf.append(text)
                    i += 1
                    continue

                # 兜底：并入当前段落
                self.buf.append(text)
                i += 1

            # 页面边界不结束题目/段落：跨页题目与段落需继续拼接

        # 收尾：最后一页的段落/题目（无 KEYS 页时不会触发中途 flush）
        self._flush()
        self._flush_question()

    # ---------- render ----------
    def title_line(self, filename: str):
        m = re.search(r"cet4_(\d{4})_(\d{2})_(\d)", filename)
        year, month, idx = (m.group(1), m.group(2), int(m.group(3))) if m else ("????", "??", 0)
        return f"# {year} 年 {month} 月大学英语四级考试真题（第 {idx} 套）"

    def render(self, filename: str):
        out = [self.title_line(filename), ""]
        for part in self.parts:
            minutes = part["minutes"].replace("minutes", "minutes")
            out.append(f"## Part {part['roman']} / {part['title']} / ({minutes})")
            out.append("")
            for section in part["sections"]:
                if section["label"]:
                    out.append(f"### Section {section['label']}")
                    out.append("")
                for block in section["blocks"]:
                    out.extend(self._render_block(block))
                if section["label"] == "A" and self.part_is_reading(part) and section.get("bank"):
                    out.extend(self._render_bank(section["bank"]))
        return "\n".join(out).rstrip() + "\n"

    @staticmethod
    def part_is_reading(part):
        return part["roman"] == "III"

    def _render_block(self, block):
        kind = block["type"]
        text = block.get("text", "")
        if kind == "directions":
            text = re.sub(r"^Directions:\s*", "", text)
            return [f"**Directions:** _{text}_", ""]
        if kind == "guide":
            return [f"**{text}**", ""]
        if kind == "passage_title":
            if text.startswith("Passage"):
                return [f"#### {text}", ""]
            return [f"**{text}**", ""]
        if kind == "para":
            return [text, ""]
        if kind == "para_label":
            return [text, ""]
        if kind == "question":
            lines = []
            opts = block["options"]
            if block["stem"]:
                lines.append(f"{block['num']}. {block['stem']}")
                for opt in opts:
                    lines.append(f"    {opt['letter']}) {opt['text']}")
            elif opts:
                lines.append(f"{block['num']}. {opts[0]['letter']}) {opts[0]['text']}")
                for opt in opts[1:]:
                    lines.append(f"    {opt['letter']}) {opt['text']}")
            else:
                lines.append(f"{block['num']}.")
            lines.append("")
            return lines
        return [text, ""]

    def _render_bank(self, bank):
        bank = sorted(bank, key=lambda b: b[0])
        rows = ["|  |  |", "| --- | --- |"]
        half = (len(bank) + 1) // 2
        for k in range(half):
            left = f"{bank[k][0]}) {bank[k][1]}"
            right = ""
            if k + half < len(bank):
                right = f"{bank[k + half][0]}) {bank[k + half][1]}"
            rows.append(f"| {left} | {right} |")
        rows.append("")
        return rows

    # ---------- summary ----------
    def summary(self):
        questions = {}
        for part in self.parts:
            for section in part["sections"]:
                for block in section["blocks"]:
                    if block["type"] == "question":
                        questions[block["num"]] = len(block["options"])
        return {
            "title": self.title_line("cet4_0000_00_0.pdf"),
            "raw_title": self.raw_title,
            "parts": [(p["roman"], p["title"], p["minutes"]) for p in self.parts],
            "question_count": len(questions),
            "missing_numbers": [n for n in range(1, 56) if n not in questions],
            "options_not_4": {n: c for n, c in questions.items() if c != 4 and n <= 25 or (n >= 46 and c != 4)},
            "bank": sum(len(sec.get("bank", [])) for p_ in self.parts for sec in p_["sections"]),
            "keys": len(self.keys),
            "keys_missing": [n for n in range(1, 56) if n not in self.keys],
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_dir", type=Path)
    ap.add_argument("out_root", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = {}
    for pdf in sorted(args.pdf_dir.glob("cet4_*_*_*.pdf")):
        parser = PaperParser(pdf)
        m = re.search(r"cet4_(\d{4})_(\d{2})_(\d)", pdf.name)
        year, month, idx = m.group(1), m.group(2), int(m.group(3))
        summary = parser.summary()
        manifest[pdf.name] = summary
        print(f"{pdf.name}: Q={summary['question_count']} missing={summary['missing_numbers']} "
              f"badopts={summary['options_not_4']} bank={summary['bank']} keys={summary['keys']} "
              f"keys_missing={summary['keys_missing']}")
        if args.dry_run:
            continue
        target_dir = args.out_root / f"{year}.{month}"
        target_dir.mkdir(parents=True, exist_ok=True)
        md = parser.render(pdf.name)
        (target_dir / f"cet4-{year}-{month}-{idx}.md").write_text(md, encoding="utf-8", newline="\n")
        (args.out_root / "keys_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )


if __name__ == "__main__":
    main()

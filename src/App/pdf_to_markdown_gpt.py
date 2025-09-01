#!/usr/bin/env python3

import os, sys, time, argparse, logging, shutil
from pathlib import Path
from typing import List, Tuple, Dict
from dotenv import load_dotenv
import pdfplumber
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4.1"
DEFAULT_MAX_INPUT_TOKENS = 20000
DEFAULT_MAX_OUTPUT_TOKENS = 5000
DEFAULT_BATCH_PAGES = 2
TOKENS_PER_CHAR = 0.25
RETRY_LIMIT = 3
RETRY_DELAY_BASE = 2.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
client = OpenAI()

def estimate_tokens(text): return int(len(text) * TOKENS_PER_CHAR)

def extract_pages(pdf_path: str) -> Dict[int, str]:
    pages = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text(layout=True) or ""
            tables = page.extract_tables()
            
            if tables:
                for table in tables:
                    if table and len(table) > 1:
                        md_table = "\n".join(["| " + " | ".join(str(cell) if cell else "" for cell in row) + " |" for row in table])
                        text += "\n\n" + md_table
            
            pages[page_num] = text
    return pages

def batch_text(batch_pages: List[Tuple[int, str]]) -> str:
    return "".join([f"\n\n--- PAGE {p} START ---\n{txt}\n--- PAGE {p} END ---\n" for p, txt in batch_pages])

def sys_prompt() -> str:
    return (
        "You are a precise PDF-to-Markdown converter. Rules:\n"
        "- Output ONLY Markdown\n"
        "- Preserve wording & punctuation\n"
        "- Rejoin broken lines/hyphens\n"
        "- Remove headers/footers/page numbers\n"
        "- Maintain reading order\n"
        "- Preserve headings, lists, tables\n"
        "- Convert tables to Markdown tables\n"
        "- Do NOT add or summarize content"
    )

def usr_prompt(text: str) -> str:
    return f"Convert the following PDF content to Markdown:\n\n{text}\n"

def gpt_call(model, system_prompt, user_prompt, max_output_tokens):
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.0,
        max_tokens=max_output_tokens,
    )
    return r.choices[0].message.content.strip()

def gpt_call_retry(*args, **kwargs):
    delay = RETRY_DELAY_BASE
    for attempt in range(RETRY_LIMIT):
        try:
            return gpt_call(*args, **kwargs)
        except Exception as e:
            if attempt == RETRY_LIMIT - 1: raise
            logger.warning("GPT call failed (%s). Retrying in %.1fs…", e, delay)
            time.sleep(delay); delay *= 2

def plan_batches(pages, max_input_tokens, start_size):
    base = estimate_tokens(sys_prompt())
    items, i, batches = list(pages.items()), 0, []
    while i < len(items):
        size = start_size
        while size > 0:
            candidate = items[i:i+size]
            toks = base + estimate_tokens(usr_prompt(batch_text(candidate)))
            if toks <= max_input_tokens:
                batches.append(candidate); i += size; break
            size -= 1
        if size == 0:
            batches.append(items[i:i+1]); i += 1
    return batches

def convert(pdf, out_dir, out_md, model, max_in, max_out, batch_pages):
    out_dir_path = Path(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    pages = extract_pages(pdf)
    batches = plan_batches(pages, max_in, batch_pages)
    sys_msg, parts = sys_prompt(), []
    for idx, batch in enumerate(batches, 1):
        file = Path(out_dir)/f"batch_{idx:03d}.md"
        if file.exists():
            content = file.read_text(encoding="utf-8")
        else:
            content = gpt_call_retry(model, sys_msg, usr_prompt(batch_text(batch)), max_out)
            file.write_text(content, encoding="utf-8")
        parts.append(content)
    Path(out_md).write_text("\n\n".join(parts).strip(), encoding="utf-8")
    logger.info("✅ Conversion complete → %s", out_md)

    if out_dir_path.exists():
        try:
            shutil.rmtree(out_dir_path)
            logger.info(f"🧹 Cleaned up batch directory: {out_dir_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup batch directory: {e}")

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set"); sys.exit(1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out_dir", default="data/markdowns/batches")
    ap.add_argument("--out_md", default="data/markdowns/output_booklet.md")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max_input_tokens", type=int, default=DEFAULT_MAX_INPUT_TOKENS)
    ap.add_argument("--max_output_tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    ap.add_argument("--batch_pages", type=int, default=DEFAULT_BATCH_PAGES)
    args = ap.parse_args()
    try:
        convert(args.pdf, args.out_dir, args.out_md, args.model,
                args.max_input_tokens, args.max_output_tokens, args.batch_pages)
    except Exception as exc:
        logger.error("❌ %s", exc); sys.exit(1)

if __name__ == "__main__":
    main()
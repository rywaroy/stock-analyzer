#!/usr/bin/env python3
"""Add stocks to stock.md, then run daily analysis and/or historical backtest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import stock_fundamental_analysis as sfa


DEFAULT_STOCK_FILE = PROJECT_ROOT / "stock.md"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "docs" / "research"


class StockEntry(NamedTuple):
    code: str
    name: str = ""


class MergeResult(NamedTuple):
    added_codes: list[str]
    skipped_codes: list[str]


class ExecutionPlan(NamedTuple):
    codes: list[str]
    daily_args: list[str]
    backtest_args: list[str]
    daily_command: str
    backtest_command: str
    output_path: Path | None


def parse_date(value: str) -> dt.date:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD") from exc


def default_from_date() -> dt.date:
    return dt.date.today() - dt.timedelta(days=365 * 3)


def clean_entry_text(value: str) -> str:
    stripped = value.strip()
    stripped = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
    return stripped.split("#", 1)[0].strip()


def split_entry_tokens(parts: list[str]) -> list[str]:
    tokens: list[str] = []
    for part in parts:
        for segment in re.split(r"[\n,，;；]+", part):
            cleaned = clean_entry_text(segment)
            if not cleaned:
                continue
            if "-" in cleaned:
                tokens.append(cleaned)
            else:
                tokens.extend(item for item in cleaned.split() if item)
    return tokens


def parse_stock_entries(parts: list[str]) -> list[StockEntry]:
    entries: list[StockEntry] = []
    index_by_code: dict[str, int] = {}
    for token in split_entry_tokens(parts):
        if "-" in token:
            raw_code, raw_name = token.split("-", 1)
            code = sfa.normalize_code(raw_code)
            name = raw_name.strip()
        else:
            code = sfa.normalize_code(token)
            name = ""
        if code in index_by_code:
            existing_index = index_by_code[code]
            existing = entries[existing_index]
            if not existing.name and name:
                entries[existing_index] = StockEntry(code, name)
            continue
        index_by_code[code] = len(entries)
        entries.append(StockEntry(code, name))
    if not entries:
        raise ValueError("请至少输入一个股票代码，例如：000001-平安银行 600519-贵州茅台")
    return entries


def format_stock_entry(entry: StockEntry) -> str:
    return f"{entry.code}-{entry.name}" if entry.name else entry.code


def existing_codes(stock_file: Path) -> set[str]:
    if not stock_file.exists():
        return set()
    return set(sfa.load_codes_from_file(stock_file))


def merge_stock_file(stock_file: str | Path, entries: list[StockEntry]) -> MergeResult:
    path = Path(stock_file).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    current_codes = existing_codes(path)
    added: list[str] = []
    skipped: list[str] = []
    original_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = list(original_lines)
    for entry in entries:
        if entry.code in current_codes:
            skipped.append(entry.code)
            continue
        lines.append(format_stock_entry(entry))
        current_codes.add(entry.code)
        added.append(entry.code)
    if lines != original_lines:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return MergeResult(added, skipped)


def compact_codes_label(codes: list[str]) -> str:
    if len(codes) <= 3:
        return "-".join(codes)
    digest = hashlib.sha1(",".join(codes).encode("utf-8")).hexdigest()[:8]
    return f"{len(codes)}stocks-{digest}"


def default_output_path(args: argparse.Namespace, codes: list[str]) -> Path:
    scope = "updated-pool" if args.backtest_scope == "all" else compact_codes_label(codes)
    return (
        DEFAULT_REPORT_DIR
        / f"stock-signal-backtest-added-{scope}-{args.from_date:%Y-%m-%d}-to-{args.to_date:%Y-%m-%d}.md"
    )


def command_text(args: list[str]) -> str:
    display_args = ["python" if item == sys.executable else item for item in args]
    return shlex.join(display_args)


def build_daily_args(args: argparse.Namespace, codes: list[str]) -> list[str]:
    if not args.run_daily:
        return []
    command = [
        sys.executable,
        str(PROJECT_ROOT / "save_daily_to_mysql.py"),
        ",".join(codes),
        "--user",
        args.user,
        "--database",
        args.database,
    ]
    if args.ingest_url:
        command.extend(["--ingest-url", args.ingest_url])
    if args.batch_size:
        command.extend(["--batch-size", str(args.batch_size)])
    if args.skip_eastmoney:
        command.append("--skip-eastmoney")
    return command


def build_backtest_args(args: argparse.Namespace, codes: list[str], output_path: Path) -> list[str]:
    if args.skip_backtest:
        return []
    command = [sys.executable, str(PROJECT_ROOT / "research_signal_backtest.py")]
    if args.backtest_scope == "all":
        command.extend(["--codes-file", str(Path(args.stock_file).expanduser())])
    else:
        command.append(",".join(codes))
    command.extend(
        [
            "--from-date",
            args.from_date.isoformat(),
            "--to-date",
            args.to_date.isoformat(),
            "--validation-from",
            args.validation_from.isoformat(),
            "--output",
            str(output_path),
            "--sample-step",
            str(args.sample_step),
            "--technical-days",
            str(args.technical_days),
            "--adjust",
            args.adjust,
            "--benchmark-index",
            args.benchmark_index,
            "--rolling-bucket",
            args.rolling_bucket,
            "--stage-fold-factors",
            args.stage_fold_factors,
        ]
    )
    return command


def build_execution_plan(args: argparse.Namespace, entries: list[StockEntry], codes: list[str]) -> ExecutionPlan:
    output_path = None if args.skip_backtest else Path(args.output).expanduser() if args.output else default_output_path(args, codes)
    daily_args = build_daily_args(args, codes)
    backtest_args = build_backtest_args(args, codes, output_path) if output_path else []
    return ExecutionPlan(
        codes=codes,
        daily_args=daily_args,
        backtest_args=backtest_args,
        daily_command=command_text(daily_args) if daily_args else "",
        backtest_command=command_text(backtest_args) if backtest_args else "",
        output_path=output_path,
    )


def run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    today = dt.date.today()
    parser = argparse.ArgumentParser(description="新增多只股票到 stock.md，并自动运行历史回测。")
    parser.add_argument("stocks", nargs="+", help="股票代码或 代码-名称，支持多个参数、逗号、中文逗号和分号分隔")
    parser.add_argument("--stock-file", default=str(DEFAULT_STOCK_FILE), help="要更新的股票池文件，默认 stock.md")
    parser.add_argument("--from-date", type=parse_date, default=default_from_date())
    parser.add_argument("--to-date", type=parse_date, default=today)
    parser.add_argument("--validation-from", type=parse_date)
    parser.add_argument("--output", default="", help="历史回测报告输出路径；不传则自动生成到 docs/research")
    parser.add_argument("--backtest-scope", choices=["added", "all"], default="added", help="added 只回测输入股票；all 回测更新后的完整股票池")
    parser.add_argument("--sample-step", type=int, default=1)
    parser.add_argument("--technical-days", type=int, default=520)
    parser.add_argument("--adjust", choices=["none", "qfq", "hfq"], default="qfq")
    parser.add_argument("--benchmark-index", default="sh000001")
    parser.add_argument("--rolling-bucket", choices=["none", "month", "quarter"], default="month")
    parser.add_argument("--stage-fold-factors", default=",".join(getattr(__import__("research_signal_backtest"), "DEFAULT_STAGE_FOLD_FACTORS")))
    parser.add_argument("--run-daily", action="store_true", help="新增后先运行 save_daily_to_mysql.py 分析输入股票")
    parser.add_argument("--skip-backtest", action="store_true", help="只新增股票，不跑历史回测")
    parser.add_argument("--user", default="root")
    parser.add_argument("--database", default="stock_analysis_test")
    parser.add_argument("--ingest-url", default="")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--skip-eastmoney", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="只展示将写入和将执行的命令，不改文件不运行")
    args = parser.parse_args(argv)
    if args.from_date > args.to_date:
        parser.error("--from-date 不能晚于 --to-date")
    if args.validation_from is None:
        span_days = (args.to_date - args.from_date).days
        args.validation_from = args.from_date + dt.timedelta(days=max(1, span_days * 2 // 3))
    if args.validation_from < args.from_date or args.validation_from > args.to_date:
        parser.error("--validation-from 必须位于回测区间内")
    if args.sample_step <= 0:
        parser.error("--sample-step 必须是正整数")
    if args.technical_days <= 0:
        parser.error("--technical-days 必须是正整数")
    if args.batch_size is not None and args.batch_size <= 0:
        parser.error("--batch-size 必须是正整数")
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        entries = parse_stock_entries(args.stocks)
        codes = [entry.code for entry in entries]
        plan = build_execution_plan(args, entries, codes)
        if args.dry_run:
            print("新增股票预览：")
            for entry in entries:
                print(f"- {format_stock_entry(entry)}")
        else:
            merge_result = merge_stock_file(args.stock_file, entries)
            print(f"stock.md 新增 {len(merge_result.added_codes)} 只，已存在跳过 {len(merge_result.skipped_codes)} 只")
        if plan.daily_command:
            print(f"日常分析命令：{plan.daily_command}")
            if not args.dry_run:
                run_command(plan.daily_args)
        if plan.backtest_command:
            print(f"历史回测命令：{plan.backtest_command}")
            if plan.output_path:
                print(f"历史回测报告：{plan.output_path}")
            if not args.dry_run:
                run_command(plan.backtest_args)
        return 0
    except Exception as exc:
        print(f"新增股票并回测失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

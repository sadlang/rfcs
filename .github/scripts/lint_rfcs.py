#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة التحقّق من صياغة مقترحات لغة ص (RFC linter).

تفحص كل ملفات المقترحات في المجلدات المعتمَدة وتتأكّد من:
  1. مطابقة اسم الملف للنمط: NNNN-اسم-وصفي.md (أربعة أرقام ثم شرطة ثم اسم).
  2. وجود حقل «الحالة» الإلزامي في الرأس بقيمة معتمَدة
     (مقترَح/مقبول/قيد التنفيذ/مكتمل/مرفوض/مؤجَّل).
  3. وجود الأقسام الإلزامية التسعة (تُطابَق بكلمات مفتاحية عربية تسامحاً مع
     اختلاف صياغة العنوان).
  4. عدم بقاء ملف باسم 0000-* (المقترح غير المرقّم لا يُدمَج).

المجلدات المفحوصة (طبقة RFC موحّدة لكل المنظومة):
  - text/        : مقترحات اللغة (مسطّحة).
  - tools/**      : مقترحات الأدوات (مجلّد فرعيّ لكل أداة، تُفحَص تعاوديًّا).
  - extensions/** : مقترحات إضافات VS Code (مجلّد فرعيّ لكل إضافة، تعاوديًّا).

تُستثنى من الفحص: أي README.md (ملف توضيحي لا مقترح).
القالب 0000-template.md يعيش في الجذر فلا يُفحَص هنا.

تُرجع رمز خروج 0 عند النجاح، و1 عند وجود أي مخالفة.
"""

import os
import re
import sys
from pathlib import Path

# فرض ترميز UTF-8 على المخرجات ليعمل السكربت على طرفيات ويندوز (cp1252/cp1255)
# كما يعمل على CI (Ubuntu) — العربية تحتاج UTF-8 صراحةً.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# جذر المستودع، ومجلدات المقترحات المعتمَدة نسبةً إليه.
REPO_ROOT = Path(__file__).resolve().parents[2]

# المجلدات المفحوصة: (المسار، هل يُفحَص تعاوديًّا؟)
#   - text/ مسطّح (مقترحات اللغة مباشرةً).
#   - tools/ و extensions/ تعاوديّان (مجلّد فرعيّ لكل أداة/إضافة).
RFC_DIRS = [
    (REPO_ROOT / "text", False),
    (REPO_ROOT / "tools", True),
    (REPO_ROOT / "extensions", True),
]

# نمط اسم الملف الصحيح: أربعة أرقام + شرطة + اسم + .md
NAME_PATTERN = re.compile(r"^\d{4}-.+\.md$")

# الأقسام الإلزامية — يكفي ورود الكلمة المفتاحية في عنوان (سطر يبدأ بـ #)
REQUIRED_SECTION_KEYWORDS = [
    "ملخّص",
    "الدافع",
    "التوجيهي",
    "المرجعي",
    "السلبيات",
    "البدائل",
    "أعمال سابقة",
    "غير محسومة",
    "مستقبلية",
]

# حقل الحالة إلزامي في رأس كل مقترح، بقيمة من القيم المعتمَدة فقط.
# نطابق تساهلاً مع/دون التشكيل (مقترَح/مقترح، مؤجَّل/مؤجل).
STATUS_FIELD_KEYWORD = "الحالة"
VALID_STATUSES = [
    "مقترَح",
    "مقترح",
    "مقبول",
    "قيد التنفيذ",
    "مكتمل",
    "مرفوض",
    "مؤجَّل",
    "مؤجل",
]

# ملفات لا تُعدّ مقترحات
IGNORED_FILES = {"README.md"}


def is_merge_context() -> bool:
    """
    هل نحن في سياق «دمج» (push إلى main)؟ في تدفّق رست، يبقى المقترح باسم
    0000- طوال فترة الـ Pull Request، ولا يُرقَّم إلا عند الدمج. لذا نفرض فحص
    الترقيم فقط عند الدفع إلى main (سياق الدمج)، ونكتفي بتحذير في الـ PR.
    """
    return (
        os.environ.get("GITHUB_EVENT_NAME") == "push"
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
    )


def collect_headings(text: str) -> str:
    """يجمع كل أسطر العناوين (التي تبدأ بـ #) في نصّ واحد للبحث فيه."""
    return "\n".join(
        line for line in text.splitlines() if line.lstrip().startswith("#")
    )


def lint_file(path: Path) -> list[str]:
    """يفحص ملف مقترح واحداً ويُرجع قائمة بالمخالفات (فارغة إن سَلِم)."""
    problems: list[str] = []
    name = path.name

    # 1) فحص اسم الملف
    #    أثناء الـ PR يُسمح بـ 0000- (لم يُرقَّم بعد)؛ غيرها يجب أن يطابق النمط.
    if name.startswith("0000-"):
        if is_merge_context():
            # عند الدمج إلى main: المقترح يجب أن يُرقَّم برقم الـ PR.
            problems.append(
                f"المقترح ما زال غير مرقّم (0000) — أعطِه رقماً قبل الدمج: {name}"
            )
        else:
            # في الـ PR: تذكير لا يُفشِل الفحص.
            print(f"   ℹ️  {name}: مقترح غير مرقّم (سيُرقَّم عند الدمج) — مقبول في الـ PR.")
    elif not NAME_PATTERN.match(name):
        problems.append(
            f"اسم الملف لا يطابق النمط 'NNNN-اسم-وصفي.md': {name}"
        )

    content = path.read_text(encoding="utf-8")

    # 2) فحص حقل «الحالة» الإلزامي في الرأس (يجب وجوده بقيمة معتمَدة)
    status_line = next(
        (
            line
            for line in content.splitlines()
            if STATUS_FIELD_KEYWORD in line and line.lstrip().startswith("-")
        ),
        None,
    )
    if status_line is None:
        problems.append(
            f"حقل إلزامي مفقود في الرأس: '{STATUS_FIELD_KEYWORD}' "
            f"(القيم المعتمَدة: {' | '.join(VALID_STATUSES)})"
        )
    elif not any(status in status_line for status in VALID_STATUSES):
        problems.append(
            f"قيمة حقل '{STATUS_FIELD_KEYWORD}' غير معتمَدة — "
            f"استخدم إحدى: {' | '.join(VALID_STATUSES)}"
        )

    # 3) فحص الأقسام الإلزامية
    headings = collect_headings(content)
    for keyword in REQUIRED_SECTION_KEYWORDS:
        if keyword not in headings:
            problems.append(f"قسم إلزامي مفقود (كلمة مفتاحية: '{keyword}')")

    return problems


def collect_candidates() -> list[Path]:
    """يجمع كل ملفات المقترحات من المجلدات المعتمَدة (مع تجاهل README وغير الموجود)."""
    candidates: list[Path] = []
    for directory, recursive in RFC_DIRS:
        if not directory.is_dir():
            continue  # مجلد اختياري قد لا يكون أُنشئ بعد (لا أدوات/إضافات حتى الآن).
        pattern = "**/*.md" if recursive else "*.md"
        candidates.extend(
            p for p in directory.glob(pattern) if p.name not in IGNORED_FILES
        )
    return sorted(candidates)


def main() -> int:
    if not any(directory.is_dir() for directory, _ in RFC_DIRS):
        print(f"::error::لا يوجد أي مجلد مقترحات: {[str(d) for d, _ in RFC_DIRS]}")
        return 1

    candidates = collect_candidates()

    if not candidates:
        print("لا توجد مقترحات لفحصها بعد — لا شيء للتحقّق منه. ✅")
        return 0

    total_problems = 0
    for path in candidates:
        rel = path.relative_to(REPO_ROOT).as_posix()
        problems = lint_file(path)
        if problems:
            total_problems += len(problems)
            print(f"\n❌ {rel}:")
            for p in problems:
                # تنسيق GitHub Actions لإظهار الخطأ على الملف
                print(f"::error file={rel}::{p}")
                print(f"   - {p}")
        else:
            print(f"✅ {rel}")

    if total_problems:
        print(f"\nالنتيجة: {total_problems} مخالفة في المقترحات.")
        return 1

    print(f"\nالنتيجة: كل المقترحات ({len(candidates)}) سليمة. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

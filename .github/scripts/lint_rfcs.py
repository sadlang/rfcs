#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة التحقّق من صياغة مقترحات لغة ص (RFC linter).

تفحص كل ملفات المقترحات في مجلد text/ وتتأكّد من:
  1. مطابقة اسم الملف للنمط: NNNN-اسم-وصفي.md (أربعة أرقام ثم شرطة ثم اسم).
  2. وجود الأقسام الإلزامية التسعة (تُطابَق بكلمات مفتاحية عربية تسامحاً مع
     اختلاف صياغة العنوان).
  3. عدم بقاء ملف باسم 0000-* (المقترح غير المرقّم لا يُدمَج).

تُستثنى من الفحص: text/README.md (ملف توضيحي لا مقترح).
القالب 0000-template.md يعيش في الجذر (خارج text/) فلا يُفحَص هنا.

تُرجع رمز خروج 0 عند النجاح، و1 عند وجود أي مخالفة.
"""

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

# مجلد المقترحات المعتمَدة (نسبةً لجذر المستودع)
TEXT_DIR = Path(__file__).resolve().parents[2] / "text"

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

# ملفات لا تُعدّ مقترحات
IGNORED_FILES = {"README.md"}


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
    if not NAME_PATTERN.match(name):
        problems.append(
            f"اسم الملف لا يطابق النمط 'NNNN-اسم-وصفي.md': {name}"
        )

    # 2) المقترح غير المرقّم (0000) لا يُدمَج
    if name.startswith("0000-"):
        problems.append(
            f"المقترح ما زال غير مرقّم (0000) — أعطِه رقماً قبل الدمج: {name}"
        )

    # 3) فحص الأقسام الإلزامية
    headings = collect_headings(path.read_text(encoding="utf-8"))
    for keyword in REQUIRED_SECTION_KEYWORDS:
        if keyword not in headings:
            problems.append(f"قسم إلزامي مفقود (كلمة مفتاحية: '{keyword}')")

    return problems


def main() -> int:
    if not TEXT_DIR.is_dir():
        print(f"::error::مجلد المقترحات غير موجود: {TEXT_DIR}")
        return 1

    candidates = [
        p
        for p in sorted(TEXT_DIR.glob("*.md"))
        if p.name not in IGNORED_FILES
    ]

    if not candidates:
        print("لا توجد مقترحات لفحصها بعد — لا شيء للتحقّق منه. ✅")
        return 0

    total_problems = 0
    for path in candidates:
        problems = lint_file(path)
        if problems:
            total_problems += len(problems)
            print(f"\n❌ {path.name}:")
            for p in problems:
                # تنسيق GitHub Actions لإظهار الخطأ على الملف
                print(f"::error file=text/{path.name}::{p}")
                print(f"   - {p}")
        else:
            print(f"✅ {path.name}")

    if total_problems:
        print(f"\nالنتيجة: {total_problems} مخالفة في المقترحات.")
        return 1

    print(f"\nالنتيجة: كل المقترحات ({len(candidates)}) سليمة. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

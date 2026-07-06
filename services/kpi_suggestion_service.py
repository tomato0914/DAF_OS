"""
DAF OS Quest63 — Expected KPI Auto Suggest サービス
DAF OS Quest65 — KPI Lesson Template サービス

Issue承認時に、Issueタイトル（必要なら本文も）からExpected KPIを
キーワードベースで自動推定する。LLMは使わない決定的な処理（MVP）。

Quest65で、KPIカテゴリ別のLesson Template（経営的な振り返り文）を追加し、
Expected KPIの一本化（Quest64）に続いて「学び」の生成もここに集約した。

必要な関数：
- infer_kpi_from_issue():     タイトル・本文からマッチしたKPI名のリストを返す
- get_categories_for_issue(): タイトル・本文がどのKPIカテゴリに一致するかを返す
                              （Quest66のconfidence_service.py等から再利用される。
                              カテゴリ判定ルールの二重管理を避けるための公開関数）
- suggest_expected_kpis():    上記を「- KPI名」形式のMarkdown箇条書き文字列に整形する
                              （decision_outcome_service.generate_outcome_template()から利用される）
- suggest_lesson_from_kpis(): KPI名リストからカテゴリ別のLesson Templateを返す
                              （reflection_service._infer_expected_kpi_and_lesson()から利用される）

推定できない場合は空リスト／「- 未設定」／「今後のKPI変化を観察し、学びを蓄積する」を返す。
例外はここで握りつぶし、呼び出し元（承認フロー・Reflection Loop・Confidence Score）を止めない。
"""

# カテゴリ別ルール（キーワード・推奨KPI・Lesson Template）。
# 複数カテゴリに一致する場合は、KPI・Lessonともにすべて集約する。
_CATEGORY_RULES: list[dict] = [
    {
        "category": "Onboarding",
        "keywords": ("オンボーディング",),
        "kpis": ("D1 Retention", "Record Completion Rate"),
        "lesson": "初回体験の分かりやすさが定着率を左右するため、オンボーディング改善は優先度高く扱う価値がある",
    },
    {
        "category": "UI / UX",
        "keywords": ("UI", "UX", "改善"),
        "kpis": ("DAU", "Retention"),
        "lesson": "UI/UX改善は日々の利用体験に直結するため、DAU・継続率への効果を優先的に検証する",
    },
    {
        "category": "Privacy / Security",
        "keywords": ("プライバシー", "セキュリティ"),
        "kpis": ("App Store Review Success", "User Trust"),
        "lesson": "法務・信頼性系Issueは審査通過やユーザー信頼に直結するため、公開前に優先して対応する価値が高い",
    },
    {
        "category": "Crash / Bug",
        "keywords": ("クラッシュ", "エラー", "不具合"),
        "kpis": ("Crash Free Rate", "Review Rating"),
        "lesson": "クラッシュ・不具合対応は早期実施によりレビュー評価の悪化を防げるため、対応の遅れはリスク拡大につながる",
    },
    {
        "category": "Marketing",
        "keywords": ("マーケティング", "紹介", "広告"),
        "kpis": ("Downloads", "New Users"),
        "lesson": "マーケティング施策はダウンロード数・新規獲得に直結するため、実施後の効果測定を徹底する",
    },
]

_FALLBACK_KPI = "未設定"
_FALLBACK_LESSON = "今後のKPI変化を観察し、学びを蓄積する"


def infer_kpi_from_issue(title: str, body: str = "") -> list[str]:
    """
    Issueタイトル・本文（任意）からキーワードマッチでKPI候補を推定する。
    複数カテゴリに一致する場合はすべて集約し、重複を除いて返す（順序は保持）。
    マッチが無ければ空リストを返す。例外を投げない。
    """
    try:
        text = f"{title or ''} {body or ''}"
        matched: list[str] = []
        for rule in _CATEGORY_RULES:
            if any(keyword in text for keyword in rule["keywords"]):
                for kpi in rule["kpis"]:
                    if kpi not in matched:
                        matched.append(kpi)
        return matched
    except Exception as e:
        print(f"[警告] KPI推定に失敗しました：{e}")
        return []


def get_categories_for_issue(title: str, body: str = "") -> list[str]:
    """
    Quest66: Issueタイトル・本文がどのKPIカテゴリ（Onboarding / UI / UX 等）に
    一致するかを返す。confidence_service.py 等、他サービスがカテゴリ判定を
    二重管理せずに再利用できるようにするための公開関数。
    マッチが無ければ空リストを返す。例外を投げない。
    """
    try:
        text = f"{title or ''} {body or ''}"
        categories: list[str] = []
        for rule in _CATEGORY_RULES:
            if any(keyword in text for keyword in rule["keywords"]):
                if rule["category"] not in categories:
                    categories.append(rule["category"])
        return categories
    except Exception as e:
        print(f"[警告] カテゴリ判定に失敗しました：{e}")
        return []


def suggest_expected_kpis(title: str, body: str = "") -> str:
    """
    infer_kpi_from_issue() の結果を「- KPI名」形式のMarkdown箇条書き文字列に整形する。
    推定できない場合は「- 未設定」を返す。例外を投げない
    （decision_outcome_service.generate_outcome_template() から呼ばれる）。
    """
    try:
        kpis = infer_kpi_from_issue(title, body)
        if not kpis:
            return f"- {_FALLBACK_KPI}"
        return "\n".join(f"- {kpi}" for kpi in kpis)
    except Exception as e:
        print(f"[警告] KPI提案の整形に失敗しました：{e}")
        return f"- {_FALLBACK_KPI}"


def suggest_lesson_from_kpis(kpis: list[str]) -> str:
    """
    Quest65: KPI名のリストから、該当するカテゴリのLesson Templateを返す。
    複数カテゴリに一致するKPIが混在する場合は、該当する学びをすべて「／」で連結する。
    どのカテゴリにも一致しない（＝カテゴリが推定できない）場合は
    「今後のKPI変化を観察し、学びを蓄積する」を返す。例外を投げない
    （reflection_service._infer_expected_kpi_and_lesson() から呼ばれる）。
    """
    try:
        if not kpis:
            return _FALLBACK_LESSON

        lessons: list[str] = []
        for rule in _CATEGORY_RULES:
            if any(kpi in rule["kpis"] for kpi in kpis) and rule["lesson"] not in lessons:
                lessons.append(rule["lesson"])

        return "／".join(lessons) if lessons else _FALLBACK_LESSON
    except Exception as e:
        print(f"[警告] Lesson推定に失敗しました：{e}")
        return _FALLBACK_LESSON

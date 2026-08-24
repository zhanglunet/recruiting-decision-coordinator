from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from validate import validate_package
except ImportError:
    validate_package = None


class PackageValidationTests(unittest.TestCase):
    def test_validator_reports_missing_manifest(self):
        self.assertIsNotNone(validate_package, "validate_package is not implemented")
        with tempfile.TemporaryDirectory() as folder:
            errors = validate_package(Path(folder))
        self.assertIn("missing file: PACKAGE.yaml", errors)

    def test_manifest_declares_three_exact_skills(self):
        manifest = (ROOT / "PACKAGE.yaml").read_text(encoding="utf-8")
        for name in (
            "shape-job-and-publishing",
            "assess-candidate-evidence",
            "design-structured-interview",
        ):
            self.assertIn(f"name: {name}", manifest)
        self.assertEqual(manifest.count("  - name:"), 3)

    def test_system_prompt_preserves_single_conclusion_authority(self):
        text = (ROOT / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
        required = (
            "职业身份",
            "工作原则",
            "专业知识",
            "专业方法",
            "专业技能",
            "工作方式",
            "输出要求",
            "招聘人员／HRBP",
            "运行契约",
            "不形成正式总分",
            "人工确认",
            "下一责任人",
        )
        for marker in required:
            self.assertIn(marker, text)
        self.assertEqual(text.count("形成跨环节的招聘推进建议"), 1)

    def test_system_prompt_routes_to_three_skills_only(self):
        text = (ROOT / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
        for skill in (
            "shape-job-and-publishing",
            "assess-candidate-evidence",
            "design-structured-interview",
        ):
            self.assertIn(skill, text)

    def test_job_skill_has_independent_intent_and_stop_rules(self):
        text = (ROOT / "skills/shape-job-and-publishing/SKILL.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "独立意图",
            "岗位实际产出",
            "必要／可培养／偏好",
            "薪资",
            "渠道字段",
            "岗位假设",
            "需确认事项",
            "不执行发布",
            "停止",
            "恢复入口",
        ):
            self.assertIn(marker, text)

    def test_candidate_skill_separates_missing_from_not_met(self):
        text = (ROOT / "skills/assess-candidate-evidence/SKILL.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "缺失信息不等于不满足",
            "证据来源定位",
            "支持程度",
            "待核证",
            "不推断诚信问题",
            "人工复核入口",
            "不改变 ATS 状态",
            "用人部门摘要",
        ):
            self.assertIn(marker, text)

    def test_candidate_skill_blocks_unauthorized_ranking_and_proxies(self):
        text = (ROOT / "skills/assess-candidate-evidence/SKILL.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "唯一适用且当前生效",
            "确定性评分服务",
            "不生成正式分数",
            "地域",
            "性别",
            "婚育",
            "年龄",
            "无岗位内在相关性的代理标签",
        ):
            self.assertIn(marker, text)

    def test_interview_skill_distinguishes_formal_and_suggested_anchors(self):
        text = (ROOT / "skills/design-structured-interview/SKILL.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "岗位产出",
            "候选待核证项",
            "提问理由",
            "可观察证据",
            "正式评分锚点",
            "建议观察点",
            "不称为正式评分标准",
            "不代替面试官评分",
            "不安排会议",
        ):
            self.assertIn(marker, text)

    def test_runtime_contract_covers_six_groups_and_receipts(self):
        text = (ROOT / "contracts/runtime-integrations.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "岗位与渠道",
            "候选与 ATS",
            "事实核验",
            "日程与会议室",
            "消息",
            "数据与指标",
            "required_not_connected",
            "partial_success",
            "权限变化",
            "空结果",
            "恢复入口",
            "Tool 成功只证明技术动作已发生",
        ):
            self.assertIn(marker, text)

    def test_runtime_contract_has_no_invented_adapter_details(self):
        text = (ROOT / "contracts/runtime-integrations.md").read_text(
            encoding="utf-8"
        )
        forbidden = ("https://", "/api/", "HTTP 200", "重试 3 次", "固定退避")
        for marker in forbidden:
            self.assertNotIn(marker, text)

    def test_readme_states_installation_and_evidence_boundaries(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "源码安装",
            "不等于平台激活",
            "required_not_connected",
            "designed_not_run",
            "Source Gate",
            "回滚",
        ):
            self.assertIn(marker, text)

    def test_all_source_assets_keep_high_impact_human_gate(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in ROOT.rglob("*.md")
            if "build" not in path.parts
        )
        for marker in ("淘汰", "面试结果", "薪资", "offer"):
            self.assertIn(marker, combined)
        self.assertNotIn("自动发送淘汰", combined)
        self.assertNotIn("自动录用", combined)


if __name__ == "__main__":
    unittest.main()

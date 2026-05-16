# tests/tests_after_developing/22_test_user_preference_scorer.py
import unittest
from unittest.mock import MagicMock
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.local_scoring.user_preference_scorer.scorer import UserPreferenceScorer
from app.models.user_preference import UserPreference


class TestUserPreferenceScorer(unittest.TestCase):

    def setUp(self):
        """测试前置准备：挂载 Mock 数据库与算子实例"""
        self.mock_db = MagicMock()
        self.scorer = UserPreferenceScorer(self.mock_db)

        self.account_id = "test_account_101"
        self.platform = "email"

    def _set_mock_rules(self, rules_list):
        """辅助方法：便捷地向 Mock 数据库中注入规则列表"""
        self.mock_db.query.return_value.filter.return_value.all.return_value = rules_list

    def test_no_rules_found_fallback(self):
        """【逻辑测试 1】无规则兜底：当账号没有任何偏好规则时，必须平稳返回 1.0 倍率"""
        self._set_mock_rules([])  # 数据库返回空

        result = self.scorer.calculate(self.account_id, self.platform)

        self.assertEqual(result["preference_factor"], 1.0)
        self.assertEqual(len(result["matched_rules"]), 0)

    def test_sender_id_exact_match(self):
        """【逻辑测试 2】精准联系人提权：验证 sender_id 能被精确匹配并赋予对应倍率"""
        # 伪造一条针对特定联系人的提权规则 (2.5倍)
        mock_rule = MagicMock(spec=UserPreference)
        mock_rule.preference_type = "sender_id"
        mock_rule.target_value = "boss@bth.se"
        mock_rule.preference_factor = 2.5

        self._set_mock_rules([mock_rule])

        # 传入匹配的 sender_id
        result = self.scorer.calculate(self.account_id, self.platform, sender_id="boss@bth.se")

        self.assertEqual(result["preference_factor"], 2.5)
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["matched_rules"][0]["target"], "boss@bth.se")

    def test_topic_fuzzy_and_case_insensitive_match(self):
        """【逻辑测试 3】话题模糊与大小写穿透：验证 topic 规则能忽略大小写，并在长句子中精准捕获关键词"""
        # 伪造一条针对 "URGENT" 关键词的降维打击规则 (5.0倍)
        mock_rule = MagicMock(spec=UserPreference)
        mock_rule.preference_type = "topic"
        mock_rule.target_value = "URGENT"  # 数据库里存的是大写
        mock_rule.preference_factor = 5.0

        self._set_mock_rules([mock_rule])

        # 传入一段小写且包含杂音的长文本
        result = self.scorer.calculate(
            self.account_id,
            self.platform,
            current_topic="This is an urgent matter regarding the server."
        )

        # 断言：必须成功忽略大小写并完成子串捕捉
        self.assertEqual(result["preference_factor"], 5.0)

    def test_multiple_rules_multiplication(self):
        """【逻辑测试 4】多维规则累乘算力：验证当同时命中发件人域和话题时，分数必须正确相乘"""
        # 规则 1：只要是 BTH 域名的邮件，权重 x 1.5
        rule_domain = MagicMock(spec=UserPreference)
        rule_domain.preference_type = "email_domain"
        rule_domain.target_value = "bth.se"
        rule_domain.preference_factor = 1.5

        # 规则 2：只要话题涉及 "project"，权重 x 2.0
        rule_topic = MagicMock(spec=UserPreference)
        rule_topic.preference_type = "topic"
        rule_topic.target_value = "project"
        rule_topic.preference_factor = 2.0

        # 规则 3：一个完全不相关的干扰规则
        rule_noise = MagicMock(spec=UserPreference)
        rule_noise.preference_type = "sender_id"
        rule_noise.target_value = "spam@ad.com"
        rule_noise.preference_factor = 0.1

        self._set_mock_rules([rule_domain, rule_topic, rule_noise])

        # 传入命中了前两者的参数
        result = self.scorer.calculate(
            self.account_id,
            self.platform,
            email_domain="BTH.SE",  # 测试域名大小写兼容
            current_topic="PA2552 Project Update",
            sender_id="teammate@bth.se"
        )

        # 💥 核心数学断言：1.5 * 2.0 必须等于 3.0，且干扰规则 0.1 绝对不能参与计算！
        self.assertEqual(result["preference_factor"], 3.0)
        self.assertEqual(len(result["matched_rules"]), 2)

    def test_unmatched_rules_ignored(self):
        """【逻辑测试 5】严格隔离测试：验证当传入参数与存在的规则皆不匹配时，不发生任何越权加分"""
        mock_rule = MagicMock(spec=UserPreference)
        mock_rule.preference_type = "sender_id"
        mock_rule.target_value = "gymbro@ig.com"
        mock_rule.preference_factor = 3.0

        self._set_mock_rules([mock_rule])

        # 传入完全不相干的人
        result = self.scorer.calculate(self.account_id, self.platform, sender_id="stranger@ig.com")

        # 必须维持 1.0 基础倍率
        self.assertEqual(result["preference_factor"], 1.0)
        self.assertEqual(len(result["matched_rules"]), 0)


if __name__ == "__main__":
    unittest.main()
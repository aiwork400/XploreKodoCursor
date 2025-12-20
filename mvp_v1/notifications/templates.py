"""
Trilingual notification templates for candidate communications.
"""

from __future__ import annotations

import config


class NotificationTemplates:
    """Trilingual notification templates for various candidate statuses."""

    @staticmethod
    def travel_ready_nepali(candidate_name: str) -> str:
        """Travel-Ready notification in Nepali."""
        return f"""
नमस्कार {candidate_name},

बधाई छ! तपाईंको यात्रा तयारी पूर्ण भएको छ।

तपाईंको सबै कागजातहरू प्रमाणित भएका छन् र तपाईं अब जापानको लागि तयार हुनुहुन्छ।

अर्को चरणहरू:
1. तपाईंको COE (Certificate of Eligibility) प्राप्त गर्नुहोस्
2. वीजा आवेदन प्रक्रिया सुरु गर्नुहोस्
3. यात्रा तिथि निर्धारण गर्नुहोस्

कुनै प्रश्नहरू छन् भने हामीलाई सम्पर्क गर्न नहिच्किचाउनुहोस्।

धन्यवाद,
XploreKodo टिम
"""

    @staticmethod
    def travel_ready_japanese(candidate_name: str) -> str:
        """Travel-Ready notification in Japanese."""
        return f"""
{candidate_name}様

おめでとうございます！あなたの旅行準備が完了しました。

すべての書類が確認され、日本への準備が整いました。

次のステップ：
1. COE（在留資格認定証明書）を取得する
2. ビザ申請プロセスを開始する
3. 旅行日を決定する

ご質問がございましたら、お気軽にお問い合わせください。

ありがとうございます。
XploreKodoチーム
"""

    @staticmethod
    def travel_ready_english(candidate_name: str) -> str:
        """Travel-Ready notification in English."""
        return f"""
Dear {candidate_name},

Congratulations! Your travel preparation is complete.

All your documents have been verified and you are now ready for Japan.

Next Steps:
1. Obtain your COE (Certificate of Eligibility)
2. Begin the visa application process
3. Schedule your travel date

If you have any questions, please don't hesitate to contact us.

Thank you,
XploreKodo Team
"""

    @classmethod
    def get_travel_ready_message(cls, candidate_name: str) -> dict[str, str]:
        """Get Travel-Ready message in all supported languages."""
        return {
            "Nepali": cls.travel_ready_nepali(candidate_name),
            "Japanese": cls.travel_ready_japanese(candidate_name),
            "English": cls.travel_ready_english(candidate_name),
        }


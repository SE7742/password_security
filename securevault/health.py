"""Kayıtlı şifrelerin toplu güç analizi ve sağlık skoru."""

import hashlib

from securevault.generator import PasswordGenerator


class PasswordHealthAnalyzer:
    """Şifre kasasındaki tüm kayıtlar için güç ve tekrar analizi."""

    @staticmethod
    def analyze_all(passwords: list[dict]) -> list[dict]:
        """Her şifre kaydını analiz eder."""
        results: list[dict] = []
        for entry in passwords:
            strength = PasswordGenerator.calculate_strength(entry.get("password", ""))
            results.append({
                "id": entry["id"],
                "site_name": entry.get("site_name", ""),
                "username": entry.get("username", ""),
                "password": entry.get("password", ""),
                "entropy": strength["entropy"],
                "score": strength["score"],
                "label": strength["label"],
                "color": strength["color"],
            })
        return results

    @staticmethod
    def find_duplicates(passwords: list[dict]) -> list[list[dict]]:
        """Aynı şifreyi kullanan kayıt gruplarını döndürür."""
        groups: dict[str, list[dict]] = {}
        for entry in passwords:
            pwd = entry.get("password", "")
            if not pwd:
                continue
            pwd_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
            groups.setdefault(pwd_hash, []).append(entry)
        return [g for g in groups.values() if len(g) > 1]

    @staticmethod
    def get_report(passwords: list[dict]) -> dict:
        """Tam sağlık raporu döndürür.

        analyze_all ve find_duplicates sonuçlarını yeniden hesaplamadan
        kullanır — O(n) yerine O(3n) redundant çağrıyı önler.
        """
        analysis = PasswordHealthAnalyzer.analyze_all(passwords)
        duplicates = PasswordHealthAnalyzer.find_duplicates(passwords)

        # Skoru mevcut analysis'ten hesapla (calculate_score'u tekrar çağırma)
        if not analysis:
            score = 100
        else:
            base_score = sum(a["score"] for a in analysis) / len(analysis)
            dup_count = sum(len(g) for g in duplicates)
            penalty = min(30, dup_count * 5)
            score = max(0, min(100, int(base_score - penalty)))

        weak = [a for a in analysis if a["score"] <= 25]
        medium = [a for a in analysis if 25 < a["score"] <= 50]
        strong = [a for a in analysis if a["score"] > 50]

        return {
            "score": score,
            "total": len(passwords),
            "analysis": analysis,
            "duplicates": duplicates,
            "weak_count": len(weak),
            "medium_count": len(medium),
            "strong_count": len(strong),
        }

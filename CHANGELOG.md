# Changelog

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」のフォーマットに従い、セマンティックバージョニング (SemVer) を採用しています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: https://semver.org/lang/ja/

## [Unreleased]

（今後の変更をここに記載します）

## [0.1.0] - 2026-03-15

Added
- パッケージ初版リリース "KabuSys"
  - パッケージ説明としてトップレベルに docstring を追加（"KabuSys - 日本株自動売買システム"）。
  - バージョン情報を定義: `__version__ = "0.1.0"`。
  - 公開 API を明示: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- 基本的なパッケージ構成を追加（スケルトン実装）
  - src/kabusys/
    - __init__.py（パッケージメタ情報）
  - サブパッケージ（プレースホルダの __init__.py を含む）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

Changed
- なし（初版）

Fixed
- なし（初版）

Security
- なし（初版）

---

注記:
- 現行のサブパッケージは雛形（空の __init__.py）であり、各モジュールの具体的な実装は今後追加される予定です。
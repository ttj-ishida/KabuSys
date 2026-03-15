Keep a Changelog
=================

すべての注目すべき変更はこのファイルで管理します。  
形式は「Keep a Changelog」に準拠しています。

フォーマット方針:
- 変更はセマンティックバージョニングに従って記載します。
- 主要なカテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security

Unreleased
----------

（現状、未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

Added
- 初期リリース: KabuSys パッケージのプロジェクト骨組みを追加
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（トップレベルのモジュールドキュメンテーション文字列に記載）
  - バージョン情報: __version__ = "0.1.0"
  - パッケージ公開 API: __all__ = ["data", "strategy", "execution", "monitoring"]
  - サブパッケージ（空のイニシャライザを含む）を作成
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - パッケージのルートファイル:
    - src/kabusys/__init__.py

Notes（推測・今後の作業）
- 現在は骨組みのみで、各サブパッケージ（data, strategy, execution, monitoring）に実装は含まれていません。今後、データ取得、取引ロジック、発注処理、監視・ログ機能などを各サブパッケージへ実装する想定です。
- セマンティックバージョニングに従い、次のマイナー/パッチ変更では機能追加やバグ修正をそれぞれ反映してください。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0
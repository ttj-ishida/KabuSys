CHANGELOG
=========
すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

フォーマット方針:
- 主要な変更はリリース単位で記載します。
- セクションは Added / Changed / Deprecated / Removed / Fixed / Security を使用します。

Unreleased
----------
今後のリリースに向けた未リリースの変更はここに記載します。

[0.1.0] - 2026-03-15
-------------------
### Added
- 初期リリース: KabuSys — 日本株自動売買システムのプロジェクトスケルトンを追加。
- パッケージのルート定義を追加:
  - src/kabusys/__init__.py
    - パッケージドキュメント文字列を追加: "KabuSys - 日本株自動売買システム"
    - バージョン番号を定義: __version__ = "0.1.0"
    - 公開モジュール一覧を定義: __all__ = ["data", "strategy", "execution", "monitoring"]
- サブパッケージの雛形（空の __init__.py）を追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
- リポジトリに最低限のパッケージ構成（モジュール境界と公開 API の定義）を整備。

### Notes
- 現時点では各サブパッケージはプレースホルダ（空の __init__.py）として存在しており、具体的な実装は含まれていません。今後のリリースでデータ取得・戦略定義・注文実行・監視機能を順次実装予定です。

References
----------
- リリース比較リンク等は必要に応じて追記してください。
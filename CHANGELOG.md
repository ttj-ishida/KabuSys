# Changelog

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog のガイドラインに準拠しています。
慣例としてセマンティックバージョニングを採用します（MAJOR.MINOR.PATCH）。

- リリース日付は YYYY-MM-DD 形式です。
- 新しい開発中の変更は Unreleased セクションに記載してください。

---

## [Unreleased]

（開発中の変更や次回リリースに向けた項目をここに記載します）

---

## [0.1.0] - 2026-03-15

初期リリース。プロジェクトの基本構成とパッケージスケルトンを追加しました。

### Added
- パッケージの初期実装を追加
  - パッケージ名: `kabusys`
  - トップレベルモジュール: `src/kabusys/__init__.py`
    - パッケージ説明ドキュメント文字列: "KabuSys - 日本株自動売買システム"
    - バージョン情報: `__version__ = "0.1.0"`
    - 公開シンボル: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - サブパッケージ（スケルトン）を追加:
    - `src/kabusys/data/__init__.py`（データ取得・管理用の名前空間）
    - `src/kabusys/strategy/__init__.py`（取引戦略の定義用の名前空間）
    - `src/kabusys/execution/__init__.py`（発注・実行ロジック用の名前空間）
    - `src/kabusys/monitoring/__init__.py`（監視・ログ・メトリクス用の名前空間）
- パッケージレイアウトを `src/` 配下に配置（一般的なビルド/配布フローに対応）

### Changed
- （該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Fixed
- （該当なし）

### Security
- （該当なし）

---

（以降のバージョンはここに追加していきます）
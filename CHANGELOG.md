# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  
※この CHANGELOG は提示されたコード（パッケージ初期化ファイル群）の内容から推測して作成しています。実際の設計意図や実装仕様と異なる可能性があります。

全般的なルール:
- 変更は逆時系列（新しいものを上）で記載しています。
- 各リリースには主なカテゴリ（Added, Changed, Fixed, Removed, Deprecated, Security）を用いています。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初期リリース。パッケージの基本構成と公開 API を確立。

### Added
- 新規パッケージ "kabusys" を追加。
  - パッケージ概要（docstring）: "KabuSys - 日本株自動売買システム"
- バージョン識別子を追加。
  - `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を定義。
- 公開モジュール一覧を定義（トップレベルのエクスポート）。
  - `__all__ = ["data", "strategy", "execution", "monitoring"]`
- 基本サブパッケージのスケルトン（空の初期化ファイル）を追加。
  - `src/kabusys/data/__init__.py` — データ取得・管理関連モジュールのための名前空間
  - `src/kabusys/strategy/__init__.py` — 売買戦略（シグナル算出等）関連の名前空間
  - `src/kabusys/execution/__init__.py` — 注文送信・約定管理等の実行層の名前空間
  - `src/kabusys/monitoring/__init__.py` — ログ、モニタリング、ヘルスチェック等の名前空間

### Changed
- （該当なし）初回リリースのため変更履歴はなし。

### Fixed
- （該当なし）

### Removed
- （該当なし）

### Deprecated
- （該当なし）

### Security
- （該当なし）

---

注: 今後、この CHANGELOG は実装の追加（例: データ取得クライアント実装、戦略の追加、注文実行ロジック、ログ/監視機能の実装など）に合わせて更新してください。
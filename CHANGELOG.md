# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは「Keep a Changelog」ガイドラインに準拠しています。
慣例に従い、セマンティック バージョニングを使用します。

フォーマット:
- Unreleased: 開発中の変更
- 各リリース: 日付付きで記載

## Unreleased
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回公開リリース

### 追加 (Added)
- 基本パッケージ `kabusys` を追加。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（src/kabusys/__init__.py のモジュールドックストリング）。
  - パッケージバージョンを定義: `__version__ = "0.1.0"`.
  - 公開対象モジュールを明示: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- 以下のサブパッケージの雛形（空の __init__.py）を追加:
  - `kabusys.data`（src/kabusys/data/__init__.py） — 市場データ取得・管理用の名前空間を想定。
  - `kabusys.strategy`（src/kabusys/strategy/__init__.py） — 売買戦略実装用の名前空間を想定。
  - `kabusys.execution`（src/kabusys/execution/__init__.py） — 注文発行・約定処理用の名前空間を想定。
  - `kabusys.monitoring`（src/kabusys/monitoring/__init__.py） — ログ・監視・アラート用の名前空間を想定。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

---

注意:
- 現状はパッケージ骨格（スケルトン構成）のみで、各サブパッケージは実装を含みません。今後のリリースで各モジュールに機能（データ取得、戦略ロジック、注文実行、監視・通知）を追加予定です。
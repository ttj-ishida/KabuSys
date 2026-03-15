# Changelog

すべての重要な変更はこのファイルで記録します。フォーマットは「Keep a Changelog」に準拠し、逆日付順（最新が上）で記載しています。

さらに詳しい情報はリポジトリ内のコミット履歴を参照してください。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システム「KabuSys」の基本的なパッケージ骨組みを追加しました。

### 追加 (Added)
- パッケージの初期モジュールを追加
  - src/kabusys/__init__.py
    - パッケージの説明ドキュメント文字列を追加（"KabuSys - 日本株自動売買システム"）。
    - __version__ = "0.1.0" を設定し、パッケージバージョンを定義。
    - __all__ に ["data", "strategy", "execution", "monitoring"] を設定し、公開サブパッケージを明示。
  - サブパッケージのスケルトンを追加（内容は空の __init__.py）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

### 変更 (Changed)
- なし（初版のため該当なし）

### 修正 (Fixed)
- なし

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

注記:
- 現時点では各サブパッケージは骨組みのみで、具体的な機能（データ取得/保存、売買戦略の実装、注文実行、監視ロジックなど）は未実装です。今後のリリースで各モジュールの具体的なインターフェースと実装を追加していきます。

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0
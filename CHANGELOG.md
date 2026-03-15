# Changelog

この CHANGELOG は「Keep a Changelog」の形式に準拠しています。  
安定したリリースからの重要な変更を時系列で記録します。

全般的なルール：
- バージョン番号はセマンティックバージョニングに従います。
- 日付はリリース日を表します。

## Unreleased

- なし

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システム「KabuSys」の基本パッケージ構成を追加しました。

### Added
- パッケージの初期実装を追加
  - `src/kabusys/__init__.py`
    - パッケージのドキュメンテーション文字列を追加（"KabuSys - 日本株自動売買システム"）。
    - パッケージバージョンを `__version__ = "0.1.0"` として定義。
    - パブリック API としてのサブパッケージを `__all__ = ["data", "strategy", "execution", "monitoring"]` で明示。
  - サブパッケージのスケルトンを追加（機能は今後実装予定）
    - `src/kabusys/data/__init__.py`（データ取得・管理用の名前空間）
    - `src/kabusys/strategy/__init__.py`（売買戦略実装用の名前空間）
    - `src/kabusys/execution/__init__.py`（注文発行・約定処理用の名前空間）
    - `src/kabusys/monitoring/__init__.py`（監視・ログ・アラート用の名前空間）

### Changed
- なし（初回リリースのため）

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注：本リリースはパッケージ構成と公開 API の骨組みを整えた段階です。各サブパッケージ内の具体的な実装（データ取得インターフェース、戦略の定義、注文実行ロジック、監視ツール等）は今後のリリースで追加・拡張されます。
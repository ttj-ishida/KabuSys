# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
安定版リリース、非互換な変更、機能追加、バグ修正などを時系列で記載してください。

フォーマット:  
- Added: 新機能
- Changed: 既存機能の変更（後方互換性があるもの）
- Deprecated: 非推奨になった機能
- Removed: 削除された機能（非互換）
- Fixed: バグ修正
- Security: セキュリティ関連の修正

## [Unreleased]
（開発中の変更はここに記載します）

## [0.1.0] - 2026-03-15

### Added
- 初期リリース（パッケージスケルトンを追加）
  - パッケージ名: `kabusys` — ドキュメンテーション用トップレベル文字列 "KabuSys - 日本株自動売買システム" を追加。
  - バージョン定義: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を追加。
  - パッケージ公開API: `__all__ = ["data", "strategy", "execution", "monitoring"]` を追加し、主要サブパッケージを明示。
  - サブパッケージのスケルトンを作成:
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - 各サブパッケージは現時点ではプレースホルダ（将来の実装のための空のモジュール）として用意。

### Changed
- なし

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

開発者向けメモ:
- 次のリリースでは各サブパッケージに具体的な実装（データ取得/管理、取引戦略、注文実行、監視・ログ機能など）を追加してください。
- バージョン番号を更新する際は `src/kabusys/__init__.py` の `__version__` を適切に変更し、本 CHANGELOG.md にリリースノートを追加してください。
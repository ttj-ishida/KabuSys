# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠し、セマンティックバージョニングを採用します。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: https://semver.org/lang/ja/

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15

初回リリース。プロジェクトの基本構造とエントリポイントを追加しました。

### Added
- パッケージ初期化ファイルを追加
  - src/kabusys/__init__.py
    - パッケージ・ドキュメンテーション文字列: "KabuSys - 日本株自動売買システム"
    - バージョン識別子: `__version__ = "0.1.0"`
    - パブリックインターフェース: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- モジュール用パッケージプレースホルダーを追加（空の初期化ファイル）
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py

### Changed
- なし

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Notes
- 現時点ではモジュールはプレースホルダー（空のパッケージ）です。今後、各サブパッケージにデータ取得（data）、取引戦略（strategy）、注文実行（execution）、監視（monitoring）に関する具体的な実装を追加していく予定です。
- パッケージの公開APIは現バージョンではモジュール名のみを公開しています。今後は各モジュール内にクラス・関数を追加し、利用者向けの安定APIを提供します。
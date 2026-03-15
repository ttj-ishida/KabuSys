# Changelog

すべての注目すべき変更点はこのファイルに記録します。形式は Keep a Changelog に準拠し、後方互換性やリリース内容の把握を容易にすることを目的とします。

項目の分類:
- Added: 新規追加
- Changed: 変更
- Fixed: 修正
- Security: セキュリティ関連

---

## [Unreleased]

現在リリース準備中の変更はここに記載します。

---

## [0.1.0] - 2026-03-15

### Added
- 初期リリース（パッケージ骨組みを追加）
  - パッケージ: `kabusys`
    - ファイル: `src/kabusys/__init__.py`
      - パッケージのドキュメンテーション文字列を追加 ("KabuSys - 日本株自動売買システム")。
      - バージョン情報を定義: `__version__ = "0.1.0"`。
      - パブリック API のエクスポートを定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
  - サブパッケージのスケルトンを追加（実装は未実装／プレースホルダ）
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - 上記によりプロジェクトの基本構成（モジュール分割と公開 API）が確立され、今後の機能実装・拡張の土台が整備された。

### Changed
- 該当なし

### Fixed
- 該当なし

### Security
- 該当なし

---

注:
- 現時点ではサブパッケージは空の初期化ファイルのみで、具体的な機能（データ取り扱い、ストラテジー定義、注文実行、監視等）は未実装です。今後のリリースで各モジュールに機能追加・公開インターフェースの確定を行う予定です。
# CHANGELOG

このファイルは「Keep a Changelog」規約に準拠しています。  
すべての日付は YYYY-MM-DD 形式で記載しています。

## Unreleased

（未リリースの変更はここに記載してください）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース（スケルトン実装）
  - パッケージルートを追加: `src/kabusys/__init__.py`
    - パッケージドキュメンテーション文字列を追加: "KabuSys - 日本株自動売買システム"
    - バージョン識別子を追加: `__version__ = "0.1.0"`
    - パッケージ外部公開インターフェースを定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - サブパッケージのスケルトンを追加（空の初期化モジュール）
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - プロジェクトの名前および目的を明示（日本株向け自動売買システムの基盤構成）

### 変更
- 該当なし（初期リリース）

### 修正
- 該当なし（初期リリース）

### 廃止予定（Deprecated）
- 該当なし

### 削除
- 該当なし

### セキュリティ
- 該当なし

---

補足（開発メモ）
- 現状はパッケージ構造の骨組みのみを含み、各サブパッケージ（data, strategy, execution, monitoring）は実装を含みません。今後のリリースで各モジュールの具体的な機能・API・テスト・ドキュメントを追加予定です。
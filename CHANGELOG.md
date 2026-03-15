# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の方針に準拠しています。バージョン番号はセマンティック バージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: KabuSys — 日本株自動売買システムのパッケージスケルトンを追加。
  - パッケージメインファイル: `src/kabusys/__init__.py`
    - パッケージドキュメンテーション文字列 ("KabuSys - 日本株自動売買システム") を設定。
    - バージョン情報を `__version__ = "0.1.0"` として定義。
    - 公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` として明示。
  - サブパッケージ（プレースホルダ）を作成:
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - ソース配置: パッケージは `src/` レイアウトで構成。

### 注意事項
- 現時点では各サブパッケージは空の初期化ファイル（プレースホルダ）のみで、具体的な実装は含まれていません。今後のリリースでデータ取得・戦略定義・注文実行・監視機能などを実装予定です。
- パッケージの基本的なインポート方法の例:
  - from kabusys import data, strategy, execution, monitoring

### 既知の制限
- 実際の取引ロジック、API クライアント、テスト、ドキュメント等は未実装のため、本バージョンはライブラリの骨組み（スケルトン）に相当します。

---

(今後の変更は上部の [Unreleased] セクションに追記してください)
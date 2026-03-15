# Changelog

すべての注目すべき変更はこのファイルに記録します。  
この変更履歴は「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）の規約に従っています。

フォーマット:
- 変更はセマンティック バージョニングに従ってタグ付けします。
- 各リリースには日付を付与します。

## Unreleased
（今後の変更をここに記載します）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: KabuSys — 日本株自動売買システムのプロジェクト骨組みを導入。
- パッケージ定義を追加:
  - src/kabusys/__init__.py にパッケージドキュメンテーション文字列を追加し、バージョン情報を設定（`__version__ = "0.1.0"`）。
  - `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義し、主要サブパッケージを公開。
- サブパッケージのスケルトンを作成:
  - src/kabusys/data/__init__.py — データ取得・管理関連のための雛形。
  - src/kabusys/strategy/__init__.py — 取引戦略関連のための雛形。
  - src/kabusys/execution/__init__.py — 注文送信・執行関連のための雛形。
  - src/kabusys/monitoring/__init__.py — 監視・ロギング・メトリクス関連のための雛形。
- ソースレイアウトは src/ 配下に配置し、パッケージ化・配布・テストの準備ができる構成に。

### 変更
- なし（初期リリースのため）。

### 修正
- なし（初期リリースのため）。

### セキュリティ
- なし（初期リリースのため）。

---

リンク（必要に応じてリポジトリ情報に置き換えてください）:  
[Unreleased]: https://github.com/<ユーザー>/<リポジトリ>/compare/v0.1.0...HEAD  
[0.1.0]: https://github.com/<ユーザー>/<リポジトリ>/releases/tag/v0.1.0
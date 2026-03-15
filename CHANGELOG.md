# Changelog

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従います。
セマンティック バージョニング（https://semver.org/lang/ja/）を採用します。

フォーマット:
- Unreleased（未リリース） — 今後の変更をここに記載します。
- 各リリースごとに日付を付けて記載します。

## [Unreleased]

（現在未登録の変更はありません）

## [0.1.0] - 2026-03-15

初期リリース。

### 追加
- 新規パッケージ `kabusys` を作成。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（トップレベル docstring）。
  - バージョン情報: `__version__ = "0.1.0"` をトップレベルに定義。
  - 公開モジュール指定: `__all__ = ["data", "strategy", "execution", "monitoring"]` を設定。
- 以下のサブパッケージ骨格を追加（現時点では各サブパッケージの __init__.py は空ファイル、将来的な実装のためのプレースホルダ）:
  - `kabusys.data` — 市場データの取得・管理を担うモジュールの想定場所。
  - `kabusys.strategy` — 売買戦略（シグナル生成・バックテスト等）を実装する想定場所。
  - `kabusys.execution` — 注文発行・約定管理・取引所とのインタフェースを担当する想定場所。
  - `kabusys.monitoring` — ロギング、モニタリング、アラート等の運用監視を担う想定場所。

### 変更
- なし（初回リリースのため）

### 修正
- なし

### 削除
- なし

---

参考:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/
- Semantic Versioning: https://semver.org/lang/ja/
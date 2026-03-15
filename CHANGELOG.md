# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」の規約に従い、セマンティック バージョニングを使用します。

現在のバージョンおよびリリース日付の記載は、リポジトリ内のソースから推測して作成しています。

## [Unreleased]
（今後の変更をここに記載します）

## [0.1.0] - 2026-03-15
初期リリース。プロジェクト骨組み（パッケージ構成）を追加。

### 追加 (Added)
- パッケージの初期構成を追加
  - src/kabusys/__init__.py
    - パッケージ docstring: "KabuSys - 日本株自動売買システム"
    - バージョン定義: __version__ = "0.1.0"
    - 公開モジュール定義: __all__ = ["data", "strategy", "execution", "monitoring"]
  - サブパッケージ（プレースホルダ）を追加
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - 上記により、以下の主要コンポーネントの骨組みを確立
    - data: 市場データの取得・整形に関するモジュールを想定
    - strategy: 売買戦略の実装・管理を想定
    - execution: 注文発注や約定処理を想定
    - monitoring: システム監視・ログ・アラート等を想定

### 注意事項
- 現状のサブパッケージは初期の空ファイル（プレースホルダ）であり、機能実装は含まれていません。今後それぞれのサブパッケージへ具体的実装（API、ユニット、ドキュメント）を追加していく予定です。
- バージョン番号はソース内の __version__ から取得しています。

---

[Unreleased]: #  
[0.1.0]: #
# CHANGELOG

この CHANGELOG は「Keep a Changelog」仕様に準拠して作成されています。  
バージョン番号はセマンティックバージョニングに従います。

- Unreleased: 進行中の変更はここに記載してください。
- リリース済みのエントリはリリース日順（新→旧）で記載します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。以下の初期パッケージ構成と基本情報を追加しました。

### 追加 (Added)
- パッケージ `kabusys` を追加。
  - 簡単なモジュール説明として、トップレベルにドキュメンテーション文字列 "KabuSys - 日本株自動売買システム" を含めています。
  - バージョン情報を `__version__ = "0.1.0"` として定義。
  - `__all__` に公開サブパッケージ一覧 ["data", "strategy", "execution", "monitoring"] を設定。

- 次のサブパッケージのスケルトン（空のパッケージイニシャライザ）を追加：
  - `kabusys.data`（src/kabusys/data/__init__.py）
  - `kabusys.strategy`（src/kabusys/strategy/__init__.py）
  - `kabusys.execution`（src/kabusys/execution/__init__.py）
  - `kabusys.monitoring`（src/kabusys/monitoring/__init__.py）

### 説明
- このリポジトリは日本株の自動売買システム "KabuSys" の初期骨格を提供します。サブパッケージはそれぞれ以下の責務を想定しています（今後の実装で拡張予定）：
  - data: 市場データの取得・整形・管理
  - strategy: 取引戦略の定義とシグナル生成
  - execution: 注文送信や約定管理といった取引実行ロジック
  - monitoring: 監視、ログ、メトリクス、アラート

### 既知の制限
- 各サブパッケージは現時点ではプレースホルダ（空の __init__ モジュール）です。機能実装は今後のリリースで追加予定です。

---
（今後のリリースでは、機能追加・バグ修正・非互換変更などを本フォーマットに従って記録します。）
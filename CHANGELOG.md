# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従い、セマンティック バージョニング（SemVer）を採用します。

フォーマットの詳細: https://keepachangelog.com/（英語）

## [Unreleased]
- 今後のリリースで予定している変更点や追加機能はここに記載します。

## [0.1.0] - 2026-03-15
初期リリース（アルファ）

### 追加
- パッケージ "kabusys" を追加。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"
  - バージョン定義: `__version__ = "0.1.0"`
  - 明示的エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- 基本モジュールの骨格を追加（空のサブパッケージとして提供）。
  - src/kabusys/data/ (`data`): データ取得・管理に関するコンポーネント用の名前空間。
  - src/kabusys/strategy/ (`strategy`): 取引戦略ロジック用の名前空間。
  - src/kabusys/execution/ (`execution`): 注文送信や取引執行のための名前空間。
  - src/kabusys/monitoring/ (`monitoring`): 監視・ロギング・アラート用の名前空間。
- 各サブパッケージは現時点では初期化ファイル（__init__.py）を備えた骨組みのみを提供。

### 変更
- 該当なし（初回リリースのため）。

### 修正
- 該当なし（初回リリースのため）。

### 注意事項 / 補足
- 本リリースはプロジェクトの初期骨格を提供するもので、具体的な機能実装（データ取得ロジック、戦略アルゴリズム、注文API連携、監視機能等）は今後のリリースで追加予定です。
- 利用例（将来的な API に合わせた想定）:
  - import kabusys
  - from kabusys import data, strategy, execution, monitoring

今後のリリースでは、それぞれのサブパッケージに具体的な機能、型定義、エラーハンドリング、テスト、ドキュメントを追加していきます。
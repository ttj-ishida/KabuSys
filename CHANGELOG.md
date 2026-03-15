# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用します。

## [Unreleased]

（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: KabuSys — 日本株自動売買システムのパッケージ骨子を追加。
- ルートパッケージを作成:
  - ファイル: `src/kabusys/__init__.py`
  - 説明: パッケージのトップレベル docstring（日本語）を追加し、バージョン情報 `__version__ = "0.1.0"` を定義。
  - エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]` を設定し、主要サブパッケージを公開。
- サブパッケージのスケルトンを追加（プレースホルダの __init__.py を配置）:
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
- リポジトリの基本構造を確立し、今後の機能実装（データ取得、戦略ロジック、注文実行、監視機能）のための土台を準備。

### 注記
- 現時点では各サブパッケージは空の初期化ファイルのみで、業務ロジックや外部依存は未実装です。
- 次の作業候補:
  - data: 市場データ取得・キャッシュ層の実装
  - strategy: 戦略インターフェースとサンプル戦略の追加
  - execution: 注文実行ラッパー（APIクライアント）の実装と安全対策
  - monitoring: ログ・アラート・メトリクス収集の実装

[0.1.0]: #
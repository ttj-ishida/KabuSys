# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記録しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

注意: リポジトリ内のコードから機能・設計を推測して記載しています（実装済みファイルの内容に基づくまとめ）。実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]

### Added
- 開発運用に向けた各種ユーティリティ・CLI を整備
  - 環境設定ウィザード `kabusys.config_setup` (.env の対話的作成/更新)
  - 設定検証 CLI `kabusys.validate_config`（.env・config/*.yaml の事前チェック）
  - Paper Trading 検証レポート生成ツール `kabusys.tools.paper_verification_report`
  - 実行エンジン起動スクリプト `run_execution.py`（ExecutionEngine 起動、paper_trading 用 DB 分離、停止フラグ/ PID 管理）
  - 監視ループ起動スクリプト `run_monitoring.py`（SystemMonitor ポーリング、停止フラグ検知、MONITOR_POLL_INTERVAL 環境変数対応）
- 設定管理の強化
  - `.env` 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）
  - .env パース処理の堅牢化（export 形式、クォートやエスケープ、インラインコメント対応）
  - `kabusys.config.Settings` による型付きアクセス（DB パス、Paper Trading 切り替え、閾値など）
- ログ & プロセス管理
  - `kabusys.utils.logging_setup.setup_logging`：stdout ストリーム + 日次ローテートファイルハンドラ（30日保持）
  - `kabusys.utils.process_priority`：Windows/Linux/macOS を吸収したプロセス優先度設定・CPU affinity 設定のユーティリティ
  - 起動時にプロセス優先度を "high" に上げる処理を起動スクリプトで実行
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - `kabusys.portfolio.portfolio_builder`：シグナル選定 (select_candidates)、等配分/スコア加重重み計算 (calc_equal_weights / calc_score_weights)
  - `kabusys.portfolio.risk_adjustment`：セクター集中上限の適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)
  - `kabusys.portfolio.position_sizing`：銘柄ごとの発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ考慮
- データ基盤の利用
  - SQLite（監視 / paper_trading 用）および DuckDB（分析用）を併用する設計を採用
  - monitoring 用 DB 初期化ヘルパー `init_monitoring_db` を起動時に確実に呼び出す
- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、paper 専用 SQLite（デフォルト: data/paper_trading.db）を利用する設計
  - MockBrokerClient を利用する想定（BrokerClientFactory 経由）
- Paper Trading の品質検証指標を出力するレポート
  - 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出・判定するレポート生成機能を追加
  - パス/フェイル閾値（稼働率 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を定義
- research モジュール（着手）
  - `kabusys.research.factor_research`：モメンタム等ファクター計算の骨組み（DuckDB 接続を受け取り price/financials を参照して計算する設計）。モメンタム指標（1M/3M/6M、MA200 乖離）等を実装予定の形で追加（途中実装を含む）

### Changed
- デフォルトのログ出力先を logs/ に統一、ログレベルは環境変数または引数で上書き可能に

### Fixed
- .env 読み込みでのエスケープ・クォート処理、インラインコメントの扱いを改善（既存の .env パースでの誤判定を回避）

### Security
- .env を生成する際に注意喚起ヘッダを出力（コミット禁止の明示）

## [0.1.0] - 2026-04-23

初期公開リリース。上記 Unreleased に列挙した主要機能を含む。

### Added
- パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）
- 基本的な自動売買プラットフォーム骨格
  - 実行エンジン起動 / 監視起動 / 環境設定ウィザード / 設定検証ツール / 検証レポートツール
- ポートフォリオ構築、リスク調整、ポジションサイジングの実装
- ロギング & プロセス制御ユーティリティ
- DuckDB を使った分析基盤導入の準備

### Changed
- N/A（初版のため過去リリースとの差分なし）

### Fixed
- N/A

### Breaking Changes
- N/A

---

開発者向け補足（コードから推測される TODO / 注意点）
- factor_research は一部実装途中で終了している（ファイル末尾の途中記述）。完全実装が必要。
- position_sizing の price 欠損時の扱いについて TODO コメントあり（フォールバック価格の検討）。
- ログディレクトリ作成失敗時はファイルロギングをスキップする挙動だが、運用時には書き込み権限等の確認が必要。
- 本番（live）環境での設定ミスを防ぐため、validate_config の実行をデプロイ前に推奨。

変更履歴の追記や修正が必要であれば、どのファイル・機能に関する差分を反映するか教えてください。
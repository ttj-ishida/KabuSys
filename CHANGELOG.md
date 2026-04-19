# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のバージョン: 0.1.0 — 2026-04-19

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージ `kabusys` を追加（__version__ = 0.1.0）。
- 環境・設定管理
  - `kabusys.config.Settings` クラスを追加し、環境変数から設定値を取得する統一 API を提供。
  - 自動 .env ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml ベース）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パース機能を強化（`export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応）。
  - 必須環境変数チェック用の `_require()` を実装。
  - Paper Trading 用の設定（`paper_sqlite_path`、`paper_fill_mode`）や監視閾値など多数のプロパティ実装。
- 設定ユーティリティ
  - 対話式環境設定ウィザード `kabusys.config_setup` を追加（.env の初期作成・更新をサポート、シークレット項目マスク表示、保存前確認）。
  - 設定検証 CLI `kabusys.validate_config` を追加（必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース検証、`--strict` フラグで警告を失敗扱いにできる）。
- 実行スクリプト
  - `run_execution.py` を追加：ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite DB（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離して動作。  
    - Broker クライアントは `BrokerClientFactory.create(settings)` で生成（Mock/実ブローカー切替）。  
    - ExecutionEngine をバックグラウンドスレッドで実行し、`data/stop_requested.flag` による停止検知/制御を実装。PID ファイル出力対応。
  - `run_monitoring.py` を追加：SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。  
    - Monitoring は KABUSYS_ENV に関わらず本番 `sqlite_path` を使用する設計（監視データは本番 DB に常時記録する意図）。  
    - 停止フラグ（プロジェクト直下 data/stop_requested.flag）検知によりループ終了。例外はロギングして次ポーリングに復帰。
- 監視/メトリクス
  - `kabusys.monitoring` 内で監視 DB 初期化（`init_monitoring_db`）を導入（冪等に監視テーブルを確保）。
- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加：  
    - stdout への StreamHandler と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。  
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。ログレベル解決順や LOG_DIR による上書き対応。
  - `kabusys.utils.process_priority` を追加：クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定 (`set_process_priority`) と CPU affinity (`set_cpu_affinity`) を提供。psutil の権限不足や未サポート時には安全にフォールバックして警告を出力。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：候補選定（score 降順・signal_rank タイブレーク）、等金額配分、スコア重み配分（全スコア 0 の場合は等金額にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`：セクター集中制限の適用（既存保有を基に新規候補を除外）、市場レジーム乗数算出（bull/neutral/bear マップ、未知レジームは警告して 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`：複数配分方式（risk_based / equal / score）に基づく株数決定ロジック、単元株丸め、per-position 上限 / aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮したコスト見積りと残余配分ロジックを実装。
  - モジュールのエクスポートを整備（kabusys.portfolio）。
- 研究用ファクターモジュール
  - `kabusys.research.factor_research` を追加：DuckDB の prices_daily / raw_financials を前提に Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（関数化、パラメータ定義、計算方針）。（注：ソースの一部が未完であり続き実装が必要）
- ツール
  - `kabusys.tools.paper_verification_report` を追加：Paper Trading の検証レポート生成スクリプト。  
    - デフォルト DB は `PAPER_TRADING_SQLITE_PATH`（環境変数）または `data/paper_trading.db`。  
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを算出し、閾値に基づき PASS/FAIL を判定。  
    - CLI オプションで日付範囲指定（--from/--to）および DB パス指定（--db）。
  - P95 計算実装（サンプルサイズが空の場合は N/A を返す）。

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

### Removed
- N/A（初期リリース）

### Security
- N/A

### Notes / Known issues / TODO
- 環境自動ロードはプロジェクトルート検出に依存するため、配布後や特殊なレイアウトでは .env が見つからない場合がある（その場合は自動ロードをスキップする）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用し手動ロードを行ってください。
- `kabusys.research.factor_research` のソースは途中で切れている（未完）。ファクター計算ロジックの完成・テストが必要。
- `apply_sector_cap` の価格が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある旨を TODO コメントで指摘。将来的にフォールバック価格（前日終値など）を採用することを検討してください。
- `calc_position_sizes` の単元丸め・スケーリングロジックは現状で共通 lot_size（デフォルト 100）想定。将来的に銘柄別単元対応に拡張予定（TODO コメントあり）。
- Process priority / affinity の設定は psutil の権限制限やプラットフォーム差分に依存するため、権限不足時は警告を出してスキップする実装（安全側）になっています。
- Monitoring は明示的に本番 sqlite_path を使う設計になっているため、テストや開発環境で監視データを分離したい場合は運用上の注意が必要（設定変更またはコード調整を検討）。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する仕様（安全フォールバック）。
- Paper Tradingの検証閾値や RiskManager の初期設定値（例: max_position_pct, max_utilization 等）はコード内定数として埋め込まれているため、運用環境では config ファイル化や環境変数による外部設定を検討してください。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の未完部完成、テスト追加
- 各種設定の YAML/外部化と更なる CLI/CI 統合
- 単体テスト・統合テストの整備とカバレッジ向上
- 銘柄別単元対応や価格フォールバックロジックの実装

（終）
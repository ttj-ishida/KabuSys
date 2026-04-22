# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
慣例: 追加 (Added)、変更 (Changed)、修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)。

## [Unreleased]

（現在のリポジトリ状態はバージョン 0.1.0 として初回公開されています。今後の変更はここに記載されます。）

---

## [0.1.0] - 2026-04-22

初回リリース。プロジェクトのコア機能および起動/運用用ツール群を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。

- 設定管理
  - `kabusys.config.Settings`：環境変数ベースの設定取得クラスを実装。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DBパス / 監視閾値 / 実行環境等）。
    - 環境変数検証（KABUSYS_ENV、LOG_LEVEL 等）とデフォルト値をサポート。
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml）を探索し、`.env` および `.env.local` を順に読み込む（OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パースはクォート、エスケープ、`export KEY=val` 形式、行内コメント（スペース直前の `#`）等に対応。

- 設定ウィザード / 検証
  - `kabusys.config_setup`：対話式 `.env` 作成/更新ウィザードを実装（`--env-file` オプション対応）。
  - `kabusys.validate_config`：起動前チェック CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の整合性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。
    - `--strict` フラグ: 警告を FAIL として扱う。

- 実行 / 監視スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - Broker クライアント抽象化（`BrokerClientFactory`）を利用し、OrderRepository / OrderManager / RiskManager / Reconciler 等の組立てを行う。
    - `RiskConfig` のデフォルト値を設定（例: max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）。
    - エンジンは別スレッドで起動し、プロジェクトルートの `data/stop_requested.flag` による `stop` 制御と `data/execution.pid` での PID 管理に対応。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値は警告の上デフォルトにフォールバック）。
    - 監視は環境（development/paper_trading/live）にかかわらず本番用 `sqlite_path` を使用。
    - 停止フラグ `data/stop_requested.flag` による終了検知、例外発生時のログ出力とループ継続処理を実装。

- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベルの解決順: argument > LOG_LEVEL 環境変数 > INFO。ログディレクトリは引数 > LOG_DIR > "logs"。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`：
    - Windows / POSIX（Linux/Mac/FreeBSD）それぞれに対するプロセス優先度設定を抽象化して提供（"high" / "normal" / "low"）。
    - `set_cpu_affinity` でプロセスの CPU affinity を最初の N コアに固定可能。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates（スコア降順で上位 N を選択）、calc_equal_weights、calc_score_weights（スコアが全て 0.0 の場合に等金額配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap（セクター集中上限に達している場合に候補を除外、"unknown" セクターは制約対象外）。
    - calc_regime_multiplier（market regime に応じた投下資金乗数を返す。'bull','neutral','bear' をサポート、未知レジームは警告の上 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算を実装。
    - 単元株丸め、ロット単位（lot_size）、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリングロジック、残余キャッシュに応じた追加配分アルゴリズムを実装。
    - 入力不備（価格欠損等）時はログ出力してスキップ。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`：DuckDB 接続を用いたファクター計算の骨格を追加。
    - モメンタムファクター（1M/3M/6M リターン、200日移動平均乖離率）などの計算ロジック方針を実装（関数雛形）。
    - DuckDB 上の prices_daily / raw_financials テーブルのみを参照する設計。

- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成ツールを実装。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - 合格基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 期間指定オプション（--from/--to）をサポート。

- DB 初期化補助
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を用いて、監視用テーブルの冪等な初期化を行う箇所を run_execution/run_monitoring で呼び出し。

### Changed
- （初回リリースにつき履歴上の変更はありません）

### Fixed
- （初回リリースにつき修正履歴はありません）

### Notes / Implementation details
- run_execution と run_monitoring は起動直後にプロセス優先度を "high" に設定しようと試みますが、権限や OS によっては設定に失敗して警告が出力されます（動作は続行されます）。
- .env の読み込みは OS 環境変数を上書きしないことを原則としつつ、`.env.local` については上書き（override=True）する挙動をサポートします（ただし OS 環境変数は保護）。
- ログは stdout を使うように設計されており、cron/Task Scheduler 等からの起動時にも扱いやすくなっています。
- Paper Trading モードでは実際のブローカー送信を行わない Mock クライアントを利用する設計想定（BrokerClientFactory により選択）。
- 一部モジュール（例: factor_research）はデータテーブル前提の計算を含むため、実行には対応する DuckDB テーブル（prices_daily / raw_financials 等）が必要です。

---

今後のバージョンでは以下のような改善を予定しています（例）:
- strategy / execution の統合テスト補強
- stocks マスタによる個別 lot_size 対応
- factor_research の完全実装およびユニットテスト追加
- モニタリング/アラートの LINE 通知連携の改善

---
# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
- 環境設定 / 管理
  - Settings クラス（kabusys.config）を追加。環境変数経由でアプリ設定を取得する API を提供。
  - 自動 .env ロード機構を導入（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パース処理を強化（export プレフィックス対応、クォートとバックスラッシュエスケープ対応、コメントルールの取り扱い）。
  - config_setup CLI（kabusys.config_setup）を追加。対話式ウィザードで .env を初期作成 / 更新可能。
  - validate_config CLI（kabusys.validate_config）を追加。必須環境変数や config/*.yaml の存在・パース検証、--strict モードで警告を FAIL 扱いに可能。
- 実行・監視ランナー
  - run_execution（kabusys/run_execution.py）を追加。ExecutionEngine の起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) のサポート。停止フラグ検知で安全に停止。
    - RiskManager に RiskConfig を渡す実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値は broker.get_available_cash() を使用。
  - run_monitoring（kabusys/run_monitoring.py）を追加。SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、監視テーブルの初期化を保証（init_monitoring_db を実行）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了。
- データベース / 分析
  - DuckDB パス、SQLite パスなどの設定プロパティを Settings に追加（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。
  - 監視テーブル初期化ヘルパー（init_monitoring_db の利用箇所を追加）。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重で重み算出（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）。売却予定銘柄をエクスポージャー計算から除外可能。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知のレジームは 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）および aggregate cap（available_cash）に基づくスケーリング実装。
    - cost_buffer による手数料・スリッページ見積り反映、スケールダウン時の残差配分ロジックを実装。
- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を提供（Windows / POSIX(nice) 対応）。失敗時は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めするユーティリティ。権限や未対応環境時は警告を出してスキップ。
- 解析 / 研究
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算（DuckDB 上の prices_daily テーブル参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などの計算（欠損データに配慮した実装）。
    - DuckDB を用いた SQL + Python の設計で、外部 API に依存しない純粋解析モジュール。
- ツール
  - tools.paper_verification_report
    - ペーパートレード用検証レポート生成 CLI を追加。--from / --to / --db オプション対応。
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - DB 欠損やテーブル欠如時に安全に N/A を返すフェールセーフを実装。
- パッケージ情報
  - __version__ を "0.1.0" に設定。

### Changed
- N/A（初回リリースのため既存コードの変更履歴なし）。

### Fixed
- N/A（初回リリースのため修正履歴なし）。

### Deprecated
- N/A

### Security
- N/A

---

注:
- 各 CLI（config_setup, validate_config, tools.paper_verification_report, run_execution, run_monitoring）はモジュールとして直接実行可能（python -m kabusys.<module>）。
- Settings が未設定の必須環境変数を検出すると ValueError を送出するため、運用前に validate_config を実行することを推奨します。
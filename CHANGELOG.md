CHANGELOG
=========

このファイルは Keep a Changelog のフォーマットに準拠して記載しています。  
（コードベースの内容からの推測に基づく変更点の要約です）

[0.1.0] - 2026-04-19
-------------------

Added
- 実行ランチャー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）による安全停止に対応。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。

- 監視ランチャー
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ検知、例外時のログ出力、KeyboardInterrupt ハンドリングを実装。

- 設定管理 / CLI
  - config.py: Settings クラスを導入し、環境変数からアプリ設定を取得。
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml）を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env のパースは引用符・エスケープ・インラインコメントに対応。
    - 各設定にバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加。
    - .env 保存前の確認、秘密項目はマスク表示、--env-file オプションをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の確認、DB パス・config/*.yaml 存在チェック、KABUSYS_ENV=live 向けの追加ガード。
    - --strict で警告を FAIL として扱う。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテート（30 日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity ユーティリティを追加。
    - Windows / POSIX (Linux, macOS 等) を吸収。権限不足や未対応環境は安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等金額・スコア加重の重み計算を追加。
  - portfolio/risk_adjustment.py: セクター集中上限適用、レジームに基づく乗数を追加。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する既定乗数を提供。未知のレジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。
    - risk_based / equal / score 方式をサポート。
    - lot_size（現状デフォルト 100）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap（スケーリング）ロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計し PASS/FAIL を判定。
    - 閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms（ソース内で定義）。
    - --from/--to/--db オプションをサポート。DB 存在チェック・テーブル欠如時の保護処理を実装。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials から Momentum / Value / Volatility / Liquidity ファクターを計算する設計を追加（calc_momentum 等の骨子実装を含む、一部未完）。

Changed
- DB の取り扱い
  - ペーパートレードは paper_sqlite_path により本番 DB と完全分離（ExecutionEngine 起動時に適用）。
  - 監視サブシステムは環境にかかわらず本番用 sqlite_path を使うことで監視データを一元化。

- ログ出力の挙動
  - logging_setup は stdout を使う（cron / Task Scheduler からのリダイレクトを想定）およびファイルハンドラの作成失敗を安全に扱うように改善。

- .env 読み込みの優先度・保護
  - OS 環境変数を保護（protected set）しつつ .env / .env.local の読み込み順を明確化（OS > .env.local > .env）。

Fixed
- .env パースの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを修正。
  - 空行やコメント行のスキップ、無効行の安全な無視を実装。

- validate_config の堅牢性
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出す（ImportError を捕捉）。

- プロセス優先度 / CPU affinity の安全化
  - 権限不足や未対応 OS に対する例外を捕捉し、警告を出して処理を継続するように変更。

Notes
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダに警告あり）。
- 主要な起動コマンド:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト値（主要なもの）
  - MONITOR_POLL_INTERVAL: 60 秒
  - LOG_DIR: logs/
  - ログローテーション: 日次、30 日分保持
  - CPU / メモリ / ディスク閾値: 90% / 85% / 90%（Settings により上書き可）
  - RiskManager の既定値（Execution 側で使用）: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20

Acknowledgements / TODOs（コードコメントより推測）
- position_sizing の lot_size を銘柄別にする拡張、価格欠損時のフォールバック（前日終値等）の追加が検討されている。
- research/factor_research はファクター実装の続き（完全な指標出力）および DuckDB 上での最適化が残っている。
- 将来的な改善点として、より詳細なエラーメトリクスや LINE 通知の統合（本番時のガード）などが想定される。

----- 

（以上は提供されたソースコードの内容から推測して作成した CHANGELOG です。必要であれば各変更項目をより詳細に分割したり、日付・バージョンを調整します。）
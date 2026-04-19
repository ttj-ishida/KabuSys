CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリースを公開。
- 基本構成・環境管理
  - Settings クラスを実装し、環境変数から各種設定（DBパス、APIトークン、ENV種別、ログレベル、監視閾値など）を取得可能に。
  - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env ファイルの柔軟なパース実装（export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - config_setup CLI（python -m kabusys.config_setup）で対話的に .env を作成・更新するウィザードを提供。
  - validate_config CLI（python -m kabusys.validate_config）で必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば）などを事前検証可能。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント抽象化に対応（本番 / モックを切替）。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止制御、実行中 PID 保存機能をサポート。
    - RiskManager の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込んで起動時に即座にリスク制約が適用されるように。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の仕様を明示。
    - 停止フラグ（data/stop_requested.flag）検知・例外耐性・KeyboardInterrupt ハンドリングを実装。
- データベース / 分析
  - SQLite（監視・注文履歴）と DuckDB（分析用）両方の接続を確立するパターンを共通化（起動スクリプトでの接続、init_monitoring_db 呼び出しでテーブル整備）。
- ロギング・プロセス管理ユーティリティ
  - logging_setup: stdout への StreamHandler と日次ローテーションされたログファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成／作成失敗時のフォールバックを実装。
  - process_priority: Windows/Linux/macOS 間の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。権限や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築（純粋関数）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバックして warning を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックして候補を除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックし警告。
  - position_sizing:
    - calc_position_sizes: 等配分・スコア配分・リスクベース（risk_based）の各 allocation_method に対応して発注株数を算出。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守見積り、再配分時の端数処理（fractional remainder に基づく追加配分）を実装。
    - 価格未取得時や price<=0 の銘柄はログ出力してスキップ。TODO コメントで将来的な価格フォールバックを明記。
- Paper Trading 用検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB から稼働率、注文成功率、送信率、レイテンシ(P95) 等を集計してレポートを生成する CLI を提供。閾値（稼働率 99%、注文成功率 90% 等）で PASS/FAIL 判定。
  - DB が存在しない場合やテーブルが無い場合の安全な取り扱い（sqlite3.OperationalError を捕捉して N/A や 0 を返す）を実装。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Known issues / Notes
- research/factor_research モジュールは計算ロジックの一部が実装中（calc_momentum の実装が途中で切れている箇所がある）。今後のリリースで完全なファクター計算を提供予定。
- position_sizing の価格フォールバック（前日終値や取得原価など）が未実装のため、open_prices に価格が欠損しているとエクスポージャーが過少見積りされる可能性がある（コード内に TODO を記載）。
- process_priority や set_cpu_affinity は権限（root/管理者）やプラットフォームの差異により期待どおり動作しない場合がある。失敗時は警告を出してスキップする実装。
- ログディレクトリ作成やファイルハンドラの作成に失敗した場合、コンソール出力にフォールバックする設計。

開発者向けメモ
- CLI エントリポイント:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 起動スクリプトはそれぞれ main を持ち、単体実行可能（if __name__ == "__main__": main()）。
- 環境変数の主なキー例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START

--- 

今後の予定（例）
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の計算と正規化）。
- ExecutionEngine/OrderManager 等の単体テスト強化および統合テスト。
- per-stock lot_size マスタ導入による銘柄別単元対応。
- 監視・アラート（LINE通知等）の拡充（現状は設定項目のみ）。
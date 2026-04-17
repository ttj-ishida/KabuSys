CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 変更はセマンティック バージョニングに従っています。
- 日付は YYYY-MM-DD 形式です。

[Unreleased]
-------------

- （現在なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース。KabuSys のコアユーティリティ、実行スクリプト、ポートフォリオ構築ロジック、検証／設定ツール、分析モジュールを提供。
- 環境/設定管理
  - Settings クラスによる環境変数中心の設定取得を実装。
  - .env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml から検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env のパースはコメント・クォート・エスケープを考慮した堅牢な実装。
  - Settings による各種既定値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）と入力検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- 対話式ウィザード
  - config_setup.py: .env を対話的に作成・更新する CLI を実装。秘密値はマスク表示、確認プロンプト、.env の安全な出力フォーマットを提供。
- 設定検証
  - validate_config.py: 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば内容検証）を行う CLI。--strict フラグで警告をエラー扱いにできる。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用して本番 DB と完全分離。
    - プロセス優先度を起動時に "high" に設定（utils.process_priority を経由）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。スレッドでエンジンを起動し、停止フラグ検知で安全に停止。
    - Execution 用コンポーネントの組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）。
    - RiskManager の初期設定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定して組み込み。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング。
- 監視 DB 初期化
  - monitoring_db の初期化呼び出しを実行スクリプト起動時に挿入（冪等で監視テーブルが存在することを保証）。
- プロセス優先度と CPU affinity
  - utils.process_priority にて Windows / POSIX の差分を吸収する set_process_priority を実装（"high"/"normal"/"low"）。失敗時は警告でスキップ。
  - set_cpu_affinity によりプロセスを先頭 N コアへピン留め可能（対応外 OS や権限不足時は警告でスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。score が全て 0 の場合は等配分へフォールバックして警告。
  - risk_adjustment: セクター集中上限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバック 1.0。
  - position_sizing: 株数決定ロジック (calc_position_sizes) を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）等を考慮した集約キャップとスケールダウン処理を実装。
    - 価格欠損・0 価格に対する安全弁やロギングを備える。
- 研究向けファクター計算
  - research.factor_research にて DuckDB を用いたファクター計算を実装（calc_momentum, calc_volatility 等）。
    - Momentum（1M/3M/6M、MA200 乖離）、ATR、平均売買代金、出来高比率などを計算。
    - データ不足時に None を返す等の堅牢化。
- Paper Trading 検証ツール
  - tools.paper_verification_report.py にて Paper Trading の検証レポート生成を実装。
    - 日付フィルタ、P95 レイテンシ計算、稼働率・注文成功率・送信率・リスク却下数の計算、閾値による PASS/FAIL 判定を出力。
    - デフォルトの DB パスは data/paper_trading.db（環境変数/--db オプションで上書き可能）。
    - データ不足やテーブル未作成時のエラーをハンドリングして N/A 表示。
- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。
  - モジュールエクスポートを整理（kabusys.portfolio 等の __all__）。

Changed
- N/A（初期リリースのため履歴なし）

Fixed
- N/A（初期リリースのため履歴なし）

Notes / Implementation details
- .env の読み込み順は OS 環境 > .env.local > .env。OS 側の既存環境変数は保護され、.env.local は上書きが可能。
- .env パーサは export KEY=val 形式、クォート内エスケープ、インラインコメント処理など多くの形式に対応。
- 各種 CLI は中断（Ctrl+C / EOF）を考慮して優雅に終了する設計。
- DuckDB 接続を受け取る関数群は外部 API を呼ばず、分析用テーブル（prices_daily, raw_financials 等）に依存。
- 本リリースではセキュリティ注意点（.env を絶対に Git にコミットしない等）を README / .env ヘッダに明記。

Closing
- 今後の予定: モックブローカーの拡張、戦略・シグナル生成パイプラインとの統合、個別銘柄の lot_size マスタ導入、テストカバレッジの拡充等。
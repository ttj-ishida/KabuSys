CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
リリース日付はコミット時点の想定日を記載しています。

Unreleased
----------

- 現在未リリースの変更はありません。

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション骨組みを実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 起動用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) による安全な終了処理を実装。
    - 監視は環境に関係なく production の sqlite_path を使用する旨を明示。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - 停止フラグと PID ファイルの取り扱いを実装。スレッドでエンジンを起動し安全に停止可能。
- 設定関連ツール
  - config_setup.py: .env の対話式ウィザードを実装。既存 .env 読み込み・編集、.env の書き出し機能を提供。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースを検証。--strict オプションで警告を fail 扱いにできる。
- 環境設定/パース
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出ロジックを含む）。
    - export プレフィックス・クォート付き値・インラインコメント等に対応した堅牢な .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - Settings クラスを実装し、J-Quants / kabuAPI / DB パス / paper trading / 監視閾値 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30 日保持）をルートロガーへ設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - ログレベル解決順序（引数 > 環境変数 > デフォルト）を明示。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity を実装。
    - Windows/Linux/macOS（サポート OS）で対応。権限不足や未対応 OS では安全にスキップ。
- Execution 内部コンポーネントの組み立て
  - run_execution.py 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler、ExecutionEngine を組み合わせて起動するフローを実装。
  - RiskConfig によるリスク制限の初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトで呼び出し、監視関連テーブルが存在することを保証（冪等）。
- Portfolio 構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額にフォールバックして警告を出す挙動を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに対する乗数(calc_regime_multiplier) を実装。
    - セクター情報がない銘柄は "unknown" 扱いでセクター上限の適用対象外とする設計。
    - レジーム値のフォールバック（未知時は 1.0）とログ警告を実装。
  - portfolio/position_sizing.py: 株数計算ロジックを実装（risk_based / equal / score の配分方式、lot_size 切り上げ・切り捨て、aggregate cap によるスケールダウン、cost_buffer の考慮など）。
    - 投入資金が available_cash を超える場合のスケーリングと残差処理（lot 単位での追加配分）を実装。
  - portfolio/__init__.py にて主要関数群をエクスポート。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加。paper trading 用 SQLite（デフォルト data/paper_trading.db）から複数指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し PASS/FAIL 判定を出力。
    - デフォルトしきい値: uptime 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms。
    - P95 計算、期間フィルタ、各種テーブルが存在しない場合のフォールバックに対応。
- Research（ファクター計算）骨格
  - research/factor_research.py にて DuckDB を用いたファクター計算モジュールの骨組み（モメンタム等）を追加（未完の部分あり）。

Changed
- ロギングの標準ストリームを stderr から stdout に変更（cron やリダイレクト環境を考慮）。
- .env 読み込み動作を改善（既存 OS 環境変数を保護する protected 機構、.env.local の上書き順序を明示）。

Fixed
- process_priority / set_cpu_affinity: 権限不足や未対応 OS 時に例外で落ちないようハンドリングを追加。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するフォールバック処理を追加し、安全にデフォルトに戻すように修正。

Security
- 環境変数の必須値が未設定のまま起動しようとした場合、Settings._require が明確なエラーを投げるようにして誤動作を防止。
- .env を生成する際にパスワード等のシークレット項目はマスク表示で確認できるように改善（config_setup.py）。

Notes / Implementation details
- 実行環境の区別
  - KABUSYS_ENV に応じて挙動を分ける（development / paper_trading / live）。paper_trading は DB とブローカーを分離して安全に検証可能。
- CLI
  - 各スクリプトはモジュール実行可能（python -m kabusys.run_monitoring 等）として設計。
- 設計方針
  - Portfolio / Position sizing / Risk adjustment / Research 等は副作用のない純粋関数として実装し、単体テストを容易にする設計を採用。

未解決 / TODO
- research/factor_research.py の一部実装が途中（コメント末尾で途切れ）。ファクター計算ロジックの完成とテスト整備が必要。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価等）については TODO コメントとして残している。
- DB スキーマや SystemMonitor / ExecutionEngine の内部実装は本 CHANGELOG のソースに含まれていないため、別途詳細リリースノートを作成予定。

-----------------------------------------------------------------------------
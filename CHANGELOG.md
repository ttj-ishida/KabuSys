# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。明示がない限り破壊的変更はないことを想定しています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-17

Added
- 全体
  - 初期リリース。システム監視、実行エンジン、環境設定ユーティリティ、ポートフォリオ構築ロジック、各種ユーティリティ、リサーチ/ファクター計算、ツール類を含む。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）は警告を出してデフォルトにフォールバックする。
    - 停止判定にプロジェクト直下の `data/stop_requested.flag` を利用。
    - 監視処理は環境（`KABUSYS_ENV`）にかかわらず本番用の `sqlite_path` を使用して初期化する（監視 DB は本番 DB を参照）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、Paper Trading 用に分離された SQLite（デフォルト `data/paper_trading.db`）を使用するように実装。
    - 実行中の PID 管理（`data/execution.pid`）と停止フラグ `data/stop_requested.flag` をサポート。
    - エンジンは別スレッドで実行され、停止フラグ検出時に安全に停止させる制御フローを実装。

- 設定管理・支援
  - config.py
    - 自動 .env 読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から検出）、OS 環境変数を上書きしない既定の挙動。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止可能。
    - `.env` のパースを堅牢化（export プレフィックス、クォート内エスケープ、インラインコメント取り扱いなど）。
    - 各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境種別判定、Paper Trading 関連設定など）。`PAPER_FILL_MODE` の妥当性チェックを実装。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。既存値の読み込み・保護（シークレットはマスク）・保存確認をサポート。
  - validate_config.py
    - 起動前に環境変数や `config/*.yaml` を検証する CLI を追加。`--strict` オプションで警告も失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップ（警告）。Live 環境向けの追加警告（LINE 設定未設定や Kill Flag 自動クリア設定）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別（スコア降順、同点は signal_rank でタイブレーク）を実装。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）を実装。既存保有のセクター別時価を算出し上限を超えるセクターから新規候補を除外。`"unknown"` セクターは上限対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップ、未知値は 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - 個別株の発注株数計算を実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer を考慮した保守的なコスト見積もり、残余キャッシュによる端数配分ロジック（lot 単位）を実装。

- リサーチ/ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum、Value、Volatility、Liquidity）を SQL / Python で計算する基盤を追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR ベースのボラティリティ、20 日平均売買代金等の計算クエリを実装（データ不足時は None で返す挙動）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）をプラットフォーム差分を吸収して実装。Windows / POSIX（Linux, Darwin, FreeBSD）を考慮し、権限不足など失敗時は警告を出してスキップする。
    - 起動スクリプトでプロセス優先度を "high" に設定する箇所を追加（run_monitoring / run_execution）。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を使用して監視テーブルの冪等初期化を各起動スクリプトで行うようにした（存在しなければ作成）。

- 実行/発注関連（骨格）
  - execution/*（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を組み合わせて ExecutionEngine を起動するフローを追加。RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を指定して起動する。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg / max / P95）などを算出して PASS/FAIL を判定する。閾値はファイル冒頭に定義（稼働率 99%、注文成功率 90%、P95 レイテンシ 200 ms など）。
    - 日付レンジ指定（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。

Changed
- なし（初期リリースのため特記事項なし）

Fixed
- なし（初期リリースのため特記事項なし）

Removed
- なし

Security
- なし

Notes / 注意事項
- 監視（run_monitoring）は設計上、本番用の `sqlite_path` を参照するようにしており、環境にかかわらず監視 DB は本番側のパスが使われる点に注意してください。
- `config.py` の自動 .env 読み込みはデフォルトで有効です。テスト環境等で自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 一部の機能（YAML パース、psutil の優先度設定等）は実行環境に依存します。該当ライブラリが存在しない／権限不足の場合は警告を出して安全にスキップする設計になっています。
- Paper Trading 時の挙動（MockBroker、別 DB 使用、PAPER_FILL_MODE の取り扱い）により実運用の DB や実注文に影響を与えないよう分離が図られていますが、設定ミスにより本番 API に接続される可能性があるため `KABUSYS_ENV` 等の設定は慎重に管理してください。
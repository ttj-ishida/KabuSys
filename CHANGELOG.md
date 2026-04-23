CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
（初期リリースに含まれる主要機能・実装ノートをコードベースから推測して記載）

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-11
------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行をスレッドで管理。
    - 停止フラグ (data/stop_requested.flag) の検知により安全に停止可能。PID ファイル (data/execution.pid) を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視(DB) は環境にかかわらず本番 sqlite_path を使用する実装方針。
    - stop フラグ検知でループ終了、例外発生時はログを記録して次ポーリングに継続。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須環境変数取得用ヘルパー、各種設定プロパティ（DB パス、paper_trading 用パス、PID/kill flag、しきい値など）を提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーション実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch など主要項目を対話的に設定し .env に保存。
- 設定検証ツール
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在/パース（PyYAML が存在する場合）等をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- 監視周り
  - monitoring_db 初期化呼び出しを実行スクリプトに組み込み（init_monitoring_db を利用して監視テーブル存在を保証）。
  - SystemMonitor の一回確認 check_once() をループから呼び出す実装。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を追加。
    - スコアが全て 0 の場合に等配分にフォールバックする挙動をログ出力。
  - portfolio/risk_adjustment.py: セクター上限適用 (apply_sector_cap)、レジーム乘数 (calc_regime_multiplier) を追加。
    - セクター上限に達した場合に新規候補を除外。unknown セクターは上限適用対象外。
    - レジーム乗数は "bull"/"neutral"/"bear" に対応（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py: 発注株数算出ロジック (calc_position_sizes) を追加。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元株 (lot_size)、max_position_pct、max_utilization、cost_buffer 等を考慮したスケーリング・端数処理を実装。
    - aggregate cap 超過時のスケールダウンと残余キャッシュに基づく追加配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化機能を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイルハンドラをスキップして標準出力のみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX を吸収して set_process_priority("high"|"normal"|"low") を提供。権限不足などで失敗した場合は警告を出して続行。
    - set_cpu_affinity により最初 N コアに固定可能（未指定時は何もしない）。
- リサーチ / ファクター計算
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数、calc_momentum のインターフェースを追加（calc_momentum は実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH を指定して、system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付レンジフィルタ（--from/--to）をサポート。
- DB/分析
  - DuckDB 接続を各種処理で利用（settings.duckdb_path）。実行・監視スクリプト両方で duckdb.connect を呼び、分析用 DB を利用可能にしている。
- 監視 DB 初期化
  - run_execution と run_monitoring の両方で init_monitoring_db を呼んで、監視用テーブルの存在を冪等的に保証。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数に秘密値（トークン/パスワード）を扱うため、config_setup で生成される .env に対して「絶対に Git にコミットしないこと」を明示。

Notes / Known issues / TODOs
- research/factor_research.calc_momentum はファイル末尾で実装途中の様子（途中で行が途切れている）。今後の実装が必要。
- position_sizing および risk_adjustment の一部に「価格欠損時のフォールバック」や「銘柄別 lot_size 対応」などの TODO コメントが残る。実運用環境では事前データの整備・検証が必要。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存のため失敗時は警告を出して処理を継続する設計。運用環境に応じた権限確認を推奨。
- .env 自動ロードの挙動は OS 環境変数を保護する（既存 env を上書かない）設計。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動ロードを無効化可能。

------------------------------------------------------------
この CHANGELOG はコードから推測して生成しています。実際の変更履歴やリリース日付はリポジトリのタグやリリースノートに準拠してください。
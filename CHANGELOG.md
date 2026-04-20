Keep a Changelog 準拠 — 変更履歴 (日本語)
=======================================

フォーマット: https://keepachangelog.com/ja/ を参照。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------
- （なし）

0.1.0 - 2026-04-20
-----------------
Added
- 基本アプリケーション骨組みを追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory に基づくブローカークライアントの生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。
    - 停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視系は常に本番 DB を参照する想定）。
    - 停止フラグ検出でループを終了。KeyboardInterrupt にも対応。
- 設定管理・CLI を追加。
  - config.py
    - .env の自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護して上書き制御）。
    - .env パースは export プレフィックス、クォート文字列、インラインコメント等に対応。
    - Settings クラスで各種環境設定（DB パス、API トークン、監視閾値、環境等）をプロパティとして提供。妥当性チェック（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新可能。
    - 標準項目セット（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を用意。
    - 既存 .env の読み込みとマスク表示（シークレット項目は **** 表示）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の問題点を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検証（PyYAML 未インストール時は警告してスキップ）。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内処理）。
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank 小さい方優先）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全てが 0 の場合は警告して等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく資金乗数（bull/neutral/bear をサポート、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight / candidates 等を元に銘柄ごとの発注株数を計算（risk_based, equal, score 対応）。
    - lot_size（デフォルト 100）で丸め、per-position 上限・aggregate cap（available_cash）を適用、cost_buffer を考慮した保守的見積。
    - aggregate scale-down の際は小数端数による再配分ロジックを実装（再現性確保のため安定ソート）。
  - portfolio パッケージ __init__ で主要関数群をエクスポート。
- utils（ユーティリティ）を追加。
  - utils.logging_setup
    - 共通のログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。既存ハンドラをクリアして重複を防止。
    - LOG_LEVEL / LOG_DIR の解決順・フォールバックをサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils.process_priority
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を用意（psutil を使用、失敗時は警告でスキップ）。
- monitoring / execution サブシステムの補助機能。
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）を各起動処理で冪等に実行して監視テーブルの存在を保証。
  - Execution 側で pid_file の扱い（pid ファイルパス設定）をサポート。
- tools
  - tools.paper_verification_report
    - ペーパートレード結果を SQLite（デフォルト data/paper_trading.db）から集計してレポート出力する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算ロジックを実装。しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
    - --from/--to/--db オプションに対応。DB が存在しない場合のメッセージを整備。
- research
  - research.factor_research（ファクター計算モジュール）を追加（設計・定数定義と初期インターフェース）。DuckDB 経由で prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等を計算する方針。注: ファイル末尾に未完の断片があり（作業途中を示唆） — 実装は継続予定。

Changed
- なし（初リリース）

Fixed
- なし（初リリース）

Notes / 設計上の重要点
- .env 自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止できる。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 や非整数）に対して警告しデフォルト 60 秒にフォールバックする処理を備える（time.sleep 例外回避）。
- run_execution は paper_trading と live（本番）で DB を完全分離する設計で、paper_trading 時は専用 DB に記録して本番データに影響を与えない。
- ロギングは stdout を StreamHandler に使用する（cron / scheduler で stdout/stderr を一本化する運用を想定）。
- process_priority / cpu_affinity の設定は権限不足や未対応環境でも安全にスキップするよう警告でハンドリングしている。

将来の作業候補（推奨）
- research.factor_research の未完部分の実装完了（SQL / DuckDB クエリ・テスト追加）。
- 銘柄別 lot_size を stocks マスタで管理する拡張（position_sizing 内 TODO）。
- price 欠損時のフォールバックロジック（前日終値等）を apply_sector_cap に追加して過小評価を避ける。
- 単体テスト・統合テストと CI 設定の追加（各 pure function と CLI のテスト化）。

--- 
（以上）
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリースを追加。
- 実行用スクリプト / 起動エントリ
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を用いる想定。
    - 停止フラグファイル (data/stop_requested.flag) の監視、実行スレッドの起動/停止制御、PID ファイル出力 (data/execution.pid) に対応。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込んでいる。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログを出力してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を利用する（monitoring 用 DB 初期化を実行）。
    - 停止フラグファイルでループを終了。
- 設定管理
  - config.py
    - .env 自動読み込み機構（プロジェクトルート検出：.git or pyproject.toml）。.env/.env.local の読み込み順と保護された OS 環境変数の扱いを実装。
    - .env パースの強化（export キーワード、クォート内のエスケープ、インラインコメントの扱い等）。
    - 各種環境設定のプロパティ化（J-Quants、kabu API、DB パス、PID/KILL フラグ、閾値など）。
    - PAPER_FILL_MODE のバリデーション、有効値制約を実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - secret 項目のマスク表示、選択肢、既存値の再利用、.env 出力フォーマットを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性をチェックする CLI を追加。
    - 必須 / 任意 env var チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリの存在確認、PyYAML インストール有無に応じた YAML 検証、live 環境に対する追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定する共通ユーティリティを追加。
    - ログディレクトリの自動作成、作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続するフェイルセーフ実装。
    - LOG_LEVEL / LOG_DIR の解決順を明確化。
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority）と CPU affinity を設定するユーティリティを追加。psutil を使い、クロスプラットフォームで差分を吸収（サポート OS と設定失敗時のフォールバックログあり）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank のタイブレーク）、等金額 / スコア加重の重み算出を実装。
    - スコアが全て 0 の場合は等金額にフォールバックする警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存ポジションに基づいて新規候補を除外する apply_sector_cap）を実装。unknown セクターは制限対象外。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、ポジション毎上限（max_position_pct）、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。
- 解析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可。
- リサーチ基盤（下地）
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤の下地を実装（モメンタム、MA200、ATR、出来高指標などの設計方針と定数群を定義、calc_momentum の実装を開始）。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 備考
- run_monitoring.py は監視用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する設計です。開発・Paper トレード等とは分離されない点に注意してください（意図的な仕様）。
- .env 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存します。失敗した場合は警告ログを出力してスキップします。
- research/factor_research.py は途中実装（calc_momentum 等の続き）です。将来的な拡張で DuckDB 上の SQL を利用した完全実装を予定しています。

謝辞
- 初期実装に貢献したすべてのコントリビュータに感謝します。
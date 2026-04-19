Keep a Changelog
=================

すべての注目すべき変更を分かりやすく記録します。  
このファイルはプロジェクトの変更履歴（CHANGELOG.md）であり、Keep a Changelog の形式に準拠します。

Unreleased
----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
--------------------

Added
- パッケージ初期リリース (バージョン: 0.1.0)
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度を "high" に設定する処理を組み込み（utils.process_priority）。
    - DB 接続:
      - 本番環境とペーパートレードで SQLite を分離（KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用）。
      - DuckDB 接続を使用（分析用）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行（デーモンスレッド）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
    - リスク設定のデフォルト値（max_position_pct 等）を Execution 側で設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視用 DB 接続は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）でループ終了。
    - 例外捕捉してループ継続する耐障害的な実装。

- 設定 / 環境管理
  - config.py
    - Settings クラスを追加。アプリ設定を環境変数から取得するためのプロパティ群を提供（J-Quants, kabu API, DB パス, Paper Trading 用設定、監視閾値、ログ設定など）。
    - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を起点に検索）。プロジェクトルートが見つかれば .env/.env.local を自動読み込み（上書きルールあり）。
    - 自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルの読み込みにおいて export プレフィックス、クォート、エスケープ、コメントルール等に対応する独自パーサ実装。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - 主要な環境変数項目群を定義し、既存 .env の読み込み・編集・保存をサポート。
    - 秘密値はマスク表示。保存前確認を行う。

  - validate_config.py
    - 起動前に .env および config/*.yaml の検証を行う CLI を追加（python -m kabusys.validate_config）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるフィルタ（売却予定銘柄を除外可能、"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマッピング。未知の値は 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に対応した株数決定ロジック。
    - 単元株丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケーリング）、cost_buffer による保守的見積り、残余金による端数配分ロジックを実装。

  - portfolio/__init__.py で上記関数をまとめてエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギングセットアップを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時はファイル出力をフォールバック。
    - 全スクリプトから呼び出して統一的ログを実現。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")：Windows の優先度クラスと POSIX の nice 値を抽象化して設定。権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count: int|None)：最初の N コアにプロセスを固定。未サポート OS / 権限不足は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - --from / --to / --db オプションをサポート。環境変数 PAPER_TRADING_SQLITE_PATH でも DB 指定可能。
    - 指標:
      - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ平均/最大/P95、リスク却下数。
    - 判定基準（デフォルトしきい値）を定義:
      - 稼働率 >= 99.0%, 注文成功率 >= 90.0%, 送信率 >= 95.0%, P95 レイテンシ <= 200 ms。
    - DB に該当テーブルがない（OperationalError）の場合でも耐性を持ってレポートを生成。

- 研究用モジュール（DuckDB ベース）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算するデザイン。
    - モメンタム計算（calc_momentum）などを実装（ファイル末尾にて実装途中の箇所あり）。

Changed
- （初回リリースのため過去変更はなし）

Fixed
- （初回リリースのため過去修正はなし）

Security
- （このリリースではセキュリティ修正は特にありません）

Notes / Migration
- 環境変数とデフォルト:
  - 自動 .env ロードの優先順位: OS 環境 > .env.local > .env
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV (development | paper_trading | live)
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - LOG_LEVEL, LOG_DIR
    - PAPER_FILL_MODE (instant|partial|never|reject)
    - KILL_FLAG_CLEAR_ON_START（本番での扱いに注意）
    - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒単位、デフォルト 60）
    - PAPER_TRADING_SQLITE_PATH（paper_verification_report / run_execution のペーパートレード DB 指定）

- 実行手順（主なエントリポイント）:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- Paper Trading の隔離:
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを完全に分離します。ブローカーは MockBrokerClient が使用されます（BrokerClientFactory により生成）。

- ロギング:
  - ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続します。

Known issues / TODO
- research/factor_research.py の一部が実装途中（ファイル末尾で calc_momentum 実装が途中で終わっている様子）。今後の開発で完成予定。
- position_sizing の price 欠損時の取り扱いに TODO コメントあり（価格欠損のフォールバック処理を検討）。
- 将来的に銘柄別の lot_size をサポートする設計に拡張予定（現状は全銘柄共通の lot_size を想定）。

Authors
- KabuSys 開発チーム（リポジトリのコードベースに基づく初回リリース）

-license
- 本 CHANGELOG はリリースノートであり、ソースコードの記載に基づいて推測・要約された内容を含みます。実際の動作や設定はソースコード（各モジュール）を参照してください。
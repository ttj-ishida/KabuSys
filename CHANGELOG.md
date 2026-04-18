# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [0.1.0] - 初回リリース
公開日: 不明

### 追加
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン: `__version__ = "0.1.0"`。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の紙面（paper）SQLite DB を使用し、本番 DB と完全に分離（デフォルト DB: `data/paper_trading.db`）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと実行スレッド管理を実装。
    - 停止フラグ(`data/stop_requested.flag`)と PID ファイル(`data/execution.pid`)の取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化を行う）。
    - 停止フラグ検知でループ終了。

- 設定・環境管理
  - config.py
    - Settings クラスを追加し、環境変数から設定を一元取得できるように。
    - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 多数のプロパティをサポート（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定など）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加（CLI: `python -m kabusys.config_setup`）。
    - セクション分けされたテンプレート出力と保存機能を提供（.env は Git にコミットしない旨を明記）。
  - validate_config.py
    - 起動前チェック CLI を追加（CLI: `python -m kabusys.validate_config`）。
    - 必須/任意環境変数の有無、KABUSYS_ENV 値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML がない場合はスキップ）を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログを `logs/<app_name>.log` に出力（30 日保持）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - `set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity(n)` を提供。権限不足などは警告でスキップ。
  - その他ユーティリティモジュールの雛形を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`) と重み計算（等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限（`apply_sector_cap`）とレジーム乗数（`calc_regime_multiplier`）を追加。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数算出ロジック（`calc_position_sizes`）を追加。risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリングを実装。
  - portfolio/__init__.py で上記 API を公開。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を用いたモメンタムなどのファクター計算モジュールの骨組みを追加（価格テーブル参照での指標算出を想定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成ツールを追加（CLI: `python -m kabusys.tools.paper_verification_report`）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し、PASS/FAIL 判定を行う。デフォルト DB は `data/paper_trading.db`。閾値に基づく判定値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの冪等初期化を実行（run_monitoring / run_execution 起動時）。

### 変更（設計上の注記）
- 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する方針。
- Execution は paper_trading のとき専用 DB を使うことで本番データと分離。

### 修正
- 環境変数パーサーの強化:
  - config._parse_env_line がシングル/ダブルクォート、バックスラッシュエスケープ、inline コメント、`export ` プレフィックス等に対応するように実装。
  - .env 自動ロードで OS 環境変数を保護（既存の OS 環境変数を上書きしない挙動 / .env.local で明示上書き可能）。

### 既知の制限・注意点
- run_monitoring のデフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可。0 以下や不正値はデフォルトにフォールバックし、警告を出力する。
- process_priority の設定は OS/権限に依存し、失敗した場合は警告で続行する。
- 一部モジュール（research の一部など）は実装継続が必要（まだ関数の途中で切れている箇所がある可能性あり）。
- .env は重要な認証情報を含むため必ず Git 管理対象から除外すること（config_setup の出力にも警告あり）。
- config/*.yaml のパース検証には PyYAML が必要。未インストール時は YAML 検証はスキップされる。

### 環境変数一覧（主なもの）
- 必須候補: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- 運用/動作
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL
  - LOG_DIR
  - MONITOR_POLL_INTERVAL
  - KILL_FLAG_CLEAR_ON_START
  - PID_FILE_PATH, KILL_FLAG_PATH
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- Paper Trading 挙動
  - PAPER_FILL_MODE (instant | partial | never | reject)

---

今後のリリースでは、research モジュールの完全実装、追加のユニットテスト、エンドツーエンドのデプロイ手順および運用ドキュメントの充実を予定しています。
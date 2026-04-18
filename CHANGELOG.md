# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを実装。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper trading 用の専用 SQLite（data/paper_trading.db 等）を使用して本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止制御: プロジェクト直下の data/stop_requested.flag の検知で安全に停止可能。実行中の PID を data/execution.pid に書く設計（pid_file 指定）。
    - プロセス優先度を起動直後に "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB に記録する設計）。
    - 停止フラグファイル（data/stop_requested.flag）でループ終了。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の優先順位や OS 環境変数の保護ロジックを実装。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / PID / kill flag /しきい値等）をプロパティで取得可能に。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH などのデフォルト値を定義。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
    - 入力補助、既存 .env の読み込み、シークレット情報のマスク表示、保存確認とファイル書き出しを実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML の存在とパースチェック、live 環境向けのガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)
    - 等配分重み (calc_equal_weights)
    - スコア加重 (calc_score_weights) — スコア全てが 0 の場合は等配分へフォールバックし警告ログ出力。
  - portfolio.position_sizing
    - ポジションサイズ計算 (calc_position_sizes)
    - allocation_method による差別化（risk_based / equal / score）
    - lot_size（単元）や max_position_pct, max_utilization, cost_buffer を考慮したスケーリングと端数処理ロジックを実装。
    - aggregate cap（全体投下額が available_cash を超える場合のスケールダウン）と残差処理を実装。
  - portfolio.risk_adjustment
    - セクター集中上限を適用する関数 (apply_sector_cap)
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を定義（bull/neutral/bear マッピング、未知レジームはフォールバックと警告）。

- 研究・ファクター計算基盤
  - research.factor_research
    - Momentum 等のファクター計算のための基盤を実装（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。
    - 定数やウィンドウ期間（1M/3M/6M/MA200/ATR 等）を定義。モメンタム計算関数の実装を開始（設計方針を含む）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を出力。
    - デフォルト DB は data/paper_trading.db。期間フィルタ（--from, --to）と --db オプションを提供。
    - 判定閾値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200 ms）を定義。

- ログ・プロセスユーティリティ
  - utils.logging_setup
    - 一元的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順を実装。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority
    - Windows / POSIX を吸収するプロセス優先度設定を実装（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢な設計。

- データベース関連
  - DuckDB と SQLite の両方を想定した設計を導入。
    - DuckDB は分析用（duckdb_path）。
    - SQLite は監視 / 注文履歴 / paper trading 用（sqlite_path / paper_sqlite_path）。
    - init_monitoring_db を起動時に呼び出して監視テーブルが存在することを保証（冪等）。

- 環境変数・機能フラグ
  - 自動 .env 読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Kill Switch / Stop Flag / PID 関連の環境変数やファイルパスをサポート（KILL_FLAG_CLEAR_ON_START 等）。
  - PAPER_FILL_MODE による paper trading の約定振る舞い制御（instant/partial/never/reject）と検証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

Notes:
- 本バージョンはコードベースから推測した初期実装の要約です。実際のリリースノートは変更履歴やコミットログに基づき追加の詳細を記載してください。
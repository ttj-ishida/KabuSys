CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。
形式は "Keep a Changelog" に準拠します。

v0.1.0 - 2026-04-19
-------------------

Added
- パッケージ初期リリース。本リリースで提供する主要機能を追加しました。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading のときはモックブローカー（MockBrokerClient）を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録する。
    - run_monitoring.py: SystemMonitor を定期ポーリングする監視ループを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag で制御。
  - 設定関連
    - config.py: .env 自動ロード機能を実装（プロジェクトルート探索: .git または pyproject.toml を基準）。Settings クラスを導入し、環境変数の取得とバリデーション、各種パス（duckdb, sqlite, paper_sqlite など）・フラグ・閾値のプロパティを提供。
    - config_setup.py: 対話式の .env ウィザードを追加（.env の初期作成・更新支援）。生成時に .env を Git にコミットしない旨を明記。
    - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。--strict モードで警告を失敗扱いにできる。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分を追加（スコアが全て 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）を考慮。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX(Linux/macOS/FreeBSD) の差分を吸収。権限不足等の失敗は警告でスキップする設計。
  - 監視・DB
    - monitoring 側初期化呼び出し（init_monitoring_db）を追加して監視テーブルの存在を保証（冪等）。monitoring は環境に関わらず production sqlite_path を使用する旨を明記。
    - duckdb と sqlite の両方をサポート（Settings でパス管理）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（P95）等を評価し PASS/FAIL 判定を出力する。CLI で期間指定・DB パス指定可能。
  - 研究モジュール（部分実装）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200、ATR、出来高系等を想定）。calc_momentum などの関数骨格を実装（作業途中の箇所あり）。

Changed
- ログ出力のポリシー
  - コンソール出力は stderr ではなく stdout に出力するように統一（cron / Task Scheduler からのリダイレクトを想定）。
- 実行時のプロセス優先度設定
  - run_execution/run_monitoring の起動直後に set_process_priority("high") を呼び出すようにして、重要プロセスの優先度を引き上げる。

Fixed
- 監視 DB 初期化の冪等性
  - run_execution でも init_monitoring_db(sqlite_conn) を呼び出し、監視テーブルが存在しない場合に生成されることを保証（本番監視データが不足するのを防止）。

Security
- .env の取り扱いに関する注意書きを config_setup.py に追加（.env を Git にコミットしないよう明記）。

Known issues / TODO
- portfolio/position_sizing.py
  - 銘柄ごとの lot_size を持たせる設計への拡張が TODO に記載（現状は全銘柄共通の lot_size を前提）。
- portfolio/risk_adjustment.py
  - price_map に値が欠損（0.0）の場合、エクスポージャーが過少評価される可能性がある点を TODO として記載。将来的に前日終値等でフォールバックする方針を検討。
- research/factor_research.py
  - ファイル末尾で calc_momentum の実装が途中で切れている（start_da...で中断）。ファクタ計算の完成が必要。
- 一部外部ライブラリ依存
  - validate_config.py の YAML 検証は PyYAML が未インストールの場合にスキップされ、警告となる（PyYAML をインストールすることで完全なパース検証が可能）。

Notes
- 環境変数関連
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
  - PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効な値は例外を投げます。
  - KILL_FLAG_CLEAR_ON_START（0/1）や PID/kill/stop フラグのパスは Settings で柔軟に変更可能です。
- package version
  - パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として設定されています。

今後
- research/factor_research の完成とファクタ正規化ユーティリティ（data.stats）との連携。
- ExecutionEngine や Monitoring のより詳細なテストカバレッジ拡充。
- 銘柄ごとの単元株情報を取り込むなど、position sizing の実用性向上。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やコミットメッセージと差異がある可能性があります。）
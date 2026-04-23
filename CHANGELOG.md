# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載します。

全般
- このリポジトリは初期バージョンとしてリリースされます。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、ペーパートレード検証レポート等を含みます。

[0.1.0] - 2026-04-23
Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用 DB を分離して利用する（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ（data/stop_requested.flag）・PID ファイル管理をサポート。プロセス優先度を起動時に設定し、Engine を別スレッドで実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する設計。停止フラグ検知で安全に終了。
- 設定管理 / ユーティリティ
  - config.py: 環境変数/.env 自動ロード機能を実装（.env, .env.local の読み込み順・上書きルール）。.git / pyproject.toml を基準にプロジェクトルートを探索して .env を自動読み込み。Settings クラスを導入し、アプリ全体の設定プロパティ（API トークン、DB パス、paper_trading 設定、監視閾値、環境種別チェック等）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザード。項目定義・既存 .env 読み込み・シークレットマスク・保存機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、YAML の存在・パースチェック（PyYAML がない場合は検証をスキップ）、本番環境向け追加警告等を実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算ロジック（allocation_method: "risk_based" / "equal" / "score"）、単元株（lot_size）丸め、ポジション上限（max_position_pct）、利用可能現金に対する aggregate cap とスケーリング、cost_buffer（手数料/スリッページ見積）等を実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームや "unknown" セクターに対するフォールバック動作を定義。
  - portfolio/__init__.py: 上記関数をエクスポート。
- モニタリング / ペーパートレード検証
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から期間指定で検証レポートを出力する CLI。稼働率（uptime）、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数（risk_logs）、レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99.0%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定を行う。引数 --from/--to/--db をサポート。DB がない場合のエラーメッセージを出力。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: setup_logging を実装。コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。既存ハンドラのクリア、ログレベル/ディレクトリ解決順を明確化。ファイルハンドラ作成失敗時は標準出力のみで継続。
  - utils/process_priority.py: set_process_priority（Windows/Linux/macOS を抽象化して優先度を設定）と set_cpu_affinity（プロセスを最初の N コアに固定）を実装。権限不足や未対応環境では警告を出してスキップする。
- その他
  - monitoring.monitoring_db.init_monitoring_db, monitoring.system_monitor 等を起動スクリプトから利用する設計で統合（監視テーブルの冪等初期化を確保）。
  - research/factor_research.py: DuckDB を用いたファクター算出モジュールの骨組み（モメンタム、MA200、ATR、出来高等）を追加（calc_momentum 等の実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
  - パッケージメタ情報: __version__ = "0.1.0"

Changed
- DB 利用方針の明記
  - run_monitoring.py: 監視は環境にかかわらず「本番 sqlite_path」を使用するよう明記（設計上の選択）。run_execution.py は paper_trading 時に専用 DB を利用するように分離。
- .env 読み込みルールの明確化
  - config.py: OS 環境変数 > .env.local（override）> .env（非上書き）が適用される。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- ログ設定
  - logging_setup.py: stdout を使用する方針（stderr ではなく stdout）を採用し、cron 等でのリダイレクト運用を想定。

Fixed
- .env パーサの堅牢化
  - config.py の _parse_env_line にて、export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォート無しでの '#' のコメント認識ルール等を正しく処理するように実装。これにより .env 内の多様な記述を安全に読めるようになった。
- 監視/実行の安全終了
  - run_execution.py / run_monitoring.py: data/stop_requested.flag による外部停止命令検知と安全停止の処理を実装。ExecutionEngine はスレッドを使用して実行し、停止フラグ検出時に engine.stop() を呼ぶ制御を追加。

Security
- 機密情報取り扱い
  - config_setup.py: 対話式ウィザードでシークレット項目は表示時にマスク。README 等への秘匿運用に関する注意書きが .env 書き込みテンプレートに含まれる（.env を Git にコミットしない旨）。

Notes / Known limitations
- research/factor_research.py はモメンタム等の実装を開始しているが、他のファクター計算・ユーティリティ（Zスコア正規化等）は別モジュール（kabusys.data.stats）に依存しており、完全な一括テストは今後の作業を要する。
- position_sizing の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過少見積りされる点）は TODO コメントで言及。将来的には前日終値などのフォールバックを導入する計画。
- process_priority / set_cpu_affinity は OS 権限や psutil の対応状況に依存する。権限不足時は警告を出してスキップする設計。

今後の予定（示唆）
- research モジュールの完全実装（全ファクター & 正規化）
- ExecutionEngine / BrokerClientFactory の統合テストおよび paper_trading の振る舞い確認
- 監視・通知（LINE）連携の実装と本番向けのガード強化
- 単体テストの追加と CI パイプライン整備

-----------
この変更履歴はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて調整してください。
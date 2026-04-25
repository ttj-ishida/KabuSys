CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

Unreleased
----------

- ドキュメント化されている TODO / 未実装箇所の追記
  - research.factor_research.calc_momentum 等、ファクター計算モジュール内に未完の実装が確認されます。今後のリリースで完成・テストを追加予定。
  - position_sizing の銘柄別 lot_size サポートなど拡張ポイントに関する注記を残しました。

0.1.0 - 2026-04-25
------------------

Added
- 初期リリース: KabuSys 自動売買システムの基本モジュール群を追加。
  - 起動スクリプト / 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離する仕組みを実装。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID 管理（data/execution.pid）をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用する設計。
  - 設定・ユーティリティ
    - config.py: 環境変数/ .env 自動読み込み機能（.env/.env.local）、プロジェクトルート自動検出、Settings クラスを導入。PAPER_FILL_MODE 等の検証ロジック、各種パス/properties を提供。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込み・マスク表示・保存までをサポート。
    - validate_config.py: .env と config/*.yaml を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス・YAML の存在とパース検証、live 環境向けのガードなどを実装。--strict オプションで警告を失敗扱いに可能。
    - utils.logging_setup: stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）をルートロガーに一元設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしても安全に動作。
    - utils.process_priority: Windows/Linux/macOS に対応したプロセス優先度（nice / priority class）設定、および CPU affinity 設定ユーティリティを追加。権限不足などの場合は警告を出してフォールバック。
  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder: 候補選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分にフォールバック。
    - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームや unknown セクターは安全にフォールバック。
    - portfolio.position_sizing: 等配分・スコア配分・リスクベース配分（risk_based）に基づき発注株数を計算する calc_position_sizes を実装。単元株（lot）丸め、1銘柄上限・集計上限（aggregate cap）のスケーリング、手数料/スリッページを考慮する cost_buffer をサポート。
  - リサーチ / ツール
    - research.factor_research: DuckDB に接続してモメンタム等のファクターを計算する初期実装を追加（設計方針と定数群を実装）。（一部関数は今後完成予定）
    - tools.paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を集計して検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定する機能を提供。--from/--to/--db のオプションをサポート。

Changed
- なし（初回リリースのため）

Fixed
- .env パーサーの改善（config._parse_env_line）
  - export KEY=val 形式のサポートを追加。
  - シングル/ダブルクォート内でのバックスラッシュエスケープを正しく扱い、インラインコメントを無視するロジックを実装。
  - クォートなしでの '#' によるコメント判定を、直前が空白 / タブの場合のみコメントとして扱う仕様に調整。
- 環境変数読み込みの保護（config._load_env_file）
  - OS 環境変数を protected にして .env/.env.local 上書きから保護する仕組みを導入（.env.local は override=True で読み込めるが OS 環境変数は上書きしない）。
- 起動スクリプトの堅牢化
  - run_monitoring.py: MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合に警告を出しデフォルト 60 秒へフォールバックする保護を追加。
  - run_execution.py / run_monitoring.py: 停止フラグ（data/stop_requested.flag）の検出、例外発生時のログ出力と継続処理、最後の DB クローズ処理を確実に行うように実装。
  - run_execution.py: paper_trading 環境での DB 分離と init_monitoring_db 呼出し（冪等）により監視テーブルが存在することを保証。
- utils.process_priority でクロスプラットフォームに対応
  - Windows 用 priority class と POSIX 系 nice 値を切り替える実装。権限不足や未対応 OS の場合は警告して処理をスキップ。

Security
- .env の扱いに関する注意を README / config_setup.py ヘッダに明記（.env を絶対にリポジトリにコミットしないことを推奨）。

Notes / Known Issues
- research.factor_research 内の一部関数が未完（ファイル末尾で途中）であり、モメンタム計算や他ファクターの SQL 実装は今後のリリースで完成予定です。
- position_sizing の将来の改善点として、銘柄別の単元（lot）をマスタから取得する拡張がコメントとして残されています。
- セクターエクスポージャー計算は price_map に依存しており、price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があります（TODO コメントあり）。将来的に価格のフォールバックを追加予定。

参考
- バージョン情報はパッケージ定義に基づき __version__ = "0.1.0" としています。
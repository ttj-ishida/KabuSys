Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリースとして以下の主要機能を追加しました。
  - CLI / 起動スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory を通じてブローカークライアントを生成。ExecutionEngine をスレッドで起動し、data/stop_requested.flag による停止制御と実行用 PID ファイルの扱いを実装。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み。initial_portfolio_value は broker.get_available_cash() から取得。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを保存。
      - stop フラグファイルでの終了検出、例外時のログ出力・リトライループを実装。
  - 設定関連ツール
    - config_setup: インタラクティブな .env ウィザードを追加（.env の初期作成・更新を支援）。シークレット項目マスク表示、デフォルト値と入力の検証、保存テンプレートを提供。
    - validate_config: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス・config/*.yaml の存在確認、KABUSYS_ENV=live 時の追加警告等を実装。--strict モードで警告をエラー扱いにできる。
  - 分析 / 検証ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を行う。P95 計算、期間フィルタ、DB パスの引数/環境変数対応を実装。
  - 設定管理
    - config.Settings クラスを追加。各種環境変数プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）を提供し、値の妥当性検査を行う。is_live / is_paper / is_dev 等のユーティリティも追加。
    - 自動 .env ロード機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。優先順位は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env ファイルのパース: export プレフィックス対応、クォート文字とバックスラッシュエスケープ対応、インラインコメント処理などを実装。
  - ロギング・プロセス制御ユーティリティ
    - utils.logging_setup.setup_logging を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。ログディレクトリの解決・作成、LOG_LEVEL/LOG_DIR の優先解決、既存ハンドラのクリア等に対応。
    - utils.process_priority に set_process_priority / set_cpu_affinity を追加。Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収し、アクセス権限や未対応 OS の場合は安全にフォールバックする。
  - ポートフォリオ構築ライブラリ
    - portfolio.portfolio_builder: 候補選定（select_candidates）と配分（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合のフォールバックロジックを実装。
    - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに基づく乗数 calc_regime_multiplier を追加。未知レジーム時のフォールバックと警告を実装。
    - portfolio.position_sizing: 株数決定ロジック calc_position_sizes を追加。allocation_method に "risk_based"/"equal"/"score" をサポートし、単元株（lot_size）丸め、per-position および aggregate cap、コストバッファを考慮したスケーリングと端数配分ロジックを実装。

Changed
- ログ出力の仕様
  - StreamHandler は stderr ではなく stdout を使用するように変更（cron / Task Scheduler でのリダイレクトを容易化）。
  - ログハンドラを再設定する際、既存ハンドラを一度 flush/close してから削除することで二重出力を防止。
- .env 読み込みポリシー
  - デフォルトの自動ロード順序を明確化（OS 環境変数 > .env.local > .env）。OS 環境変数は保護され、.env.local による上書きでも保護されるように配慮。

Fixed / Robustness
- .env パーサーの堅牢化
  - export プレフィックスやクォートされた値（バックスラッシュエスケープ含む）、およびインラインコメントの取り扱いに対応し、より現実的な .env フォーマットを正しく扱えるようにした。
- プロセス優先度 / CPU affinity の例外処理を強化
  - 権限不足や未実装 API に対して警告を出しつつ安全にスキップするようにして、起動の失敗を回避。
- 監視/実行周りの DB 初期化の冪等性
  - init_monitoring_db を使用して監視テーブルの存在を保証（複数起動時の安全性向上）。

Security
- config_setup が生成する .env テンプレートに "絶対に Git にコミットしないこと" の注意を明記。

Notes / その他
- Settings.paper_fill_mode 等で受け入れる値の妥当性チェックを導入（不正値時は ValueError を送出）。
- research モジュール（factor_research 等）は DuckDB を用いたファクター計算の骨格を提供。prices_daily / raw_financials テーブルのみ参照する設計。
- バージョンはパッケージトップで __version__ = "0.1.0" に設定。

今後の予定（例）
- ExecutionEngine / BrokerClient の統合テスト・モック整備。
- portfolio の lot_size を銘柄別に扱えるよう拡張。
- monitor / execution の起動監視（systemd / supervisor 用のユーティリティ）やより細かいアラート設定（LINE 通知の自動化）。

---------------------------------------
[0.1.0]: 2026-04-19
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
フォーマットについて: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメント/テスト用の変更はありません（次回リリースに反映予定）。

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース。KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築ロジック・検証ツールを追加。
  - 起動スクリプト
    - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し MockBrokerClient を利用することで本番 DB と完全に分離。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視機能は環境にかかわらず本番の sqlite_path を使用する旨を明示。
  - 設定管理
    - config: .env 自動読み込み機能（プロジェクトルート検出）を実装。.env/.env.local の読み込み順を実装し、OS 環境変数を保護する protected パラメータを導入。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 他多数の設定プロパティを提供。PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - config_setup: .env 作成・更新の対話式ウィザードを追加（ウィザードでの既存値読み込み、シークレットマスク表示、保存機能）。
    - validate_config: 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パス、config/*.yaml の存在と YAML パース検証、live 環境向けガード）。--strict モードをサポート。
  - ロギング / プロセス管理
    - utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ作成失敗時のフォールバックやログレベル解決ロジックを実装。
    - utils.process_priority: psutil を用いたプロセス優先度設定機能を追加（Windows/Linux/macOS 対応）。CPU affinity を固定する set_cpu_affinity も実装。
  - Execution / Monitoring 周辺
    - run_execution における依存組み立て（BrokerClientFactory / OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を実装。RiskManager のデフォルト設定を提供し、ExecutionEngine の起動・停止制御（PID ファイル・停止フラグ）を整備。
    - run_monitoring で monitoring DB の初期化（init_monitoring_db）と DuckDB 接続を行い SystemMonitor.check_once() をポーリング実行。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: シグナルの選別（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装（スコア全0 のフォールバックロジック含む）。
    - portfolio.risk_adjustment: セクター集中の上限チェック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（未知レジームはフォールバックして警告）。
    - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。単元（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積などをサポート。
  - Research / 分析ツール
    - research.factor_research: モメンタム等のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針）。（注: ファイル末端に続きあり）
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを計算し、閾値に基づく PASS/FAIL 判定を実装。PAPER_TRADING_SQLITE_PATH 環境変数／--db オプション対応。

Changed
- （初回リリースのため履歴上の「変更」はありません）

Fixed
- （初回リリースのため履歴上の「修正」はありません）

Security
- シークレット値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE チャンネルなど）は Settings で必須チェック・config_setup でマスク表示するなど取り扱いに配慮。

Notes / 注意事項
- run_monitoring は監視データ用 SQLite のパス（Settings.sqlite_path）を使用しますが、monitoring 用 DB は環境にかかわらず production 用パスを参照する設計になっています。Paper Trading の完全分離を期待する場合は run_execution（paper_sqlite_path）を使用してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を見つけられない場合はスキップされます。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KILL_FLAG_CLEAR_ON_START は本番環境ではリスクがあるためデフォルトは 0（クリアしない）です。validate_config で live 環境時の警告を行います。
- process_priority / cpu_affinity の設定は権限不足や未対応プラットフォームではスキップされ、警告が出力されます（実行を妨げません）。
- ログディレクトリ作成に失敗した場合はファイル出力を行わず標準出力のみでログを継続します。

開発者向け補足
- パッケージバージョンは __version__ = "0.1.0" に設定済み。
- 今後の作業予定（候補）
  - research.factor_research の完全実装とユニットテスト追加。
  - ExecutionEngine / BrokerClient のモックを用いた統合テストの整備。
  - 単体テスト（特に position_sizing・risk_adjustment のロジック）と CI の導入。

---  
以上。必要であれば、各モジュールごとのより詳細な変更点（関数仕様・環境変数一覧・サンプル .env）を追加で出力できます。
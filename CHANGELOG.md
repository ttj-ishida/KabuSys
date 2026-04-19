CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
このファイルは「Keep a Changelog」の形式に準拠します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーションの初期リリース。
  - パッケージバージョン: 0.1.0
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の際は MockBrokerClient と paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を監視して安全に停止可能。
  - run_monitoring.py: 監視ループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検出・例外安全なループ処理を実装。
- 設定管理
  - config.py: 環境変数/.env の読み込み・アクセスを行う Settings クラスを追加。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数要求（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_sqlite_path, duckdb_path, sqlite_path, 各種監視閾値や PID/kill flag パスの取得ユーティリティ。
- 設定用 CLI / ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 項目の説明・デフォルト・シークレット入力対応。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 稼働率、注文成功率・送信率、レイテンシ（平均/最大/P95）、リスク却下数などを算出して PASS/FAIL 判定を出力。
    - コマンドライン引数 --from / --to / --db および環境変数 PAPER_TRADING_SQLITE_PATH に対応。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知レジームはフォールバックして 1.0 を返却。ログ出力で警告。
  - portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score）を実装。
    - 単元（lot_size）丸め、ポジション上限・aggregate cap（available_cash に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積）処理を実装。
    - 打ち切り・再配分ロジック（小数端数の補填）を含む。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout ストリームハンドラ＋日次ローテートの TimedRotatingFileHandler（既定 logs/ ディレクトリ、30 日保持）。
    - LOG_DIR 環境変数や引数で上書き可能。ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS を抽象化して set_process_priority/set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時には警告ログでスキップ。
- データベース
  - DuckDB を分析用に使用（duckdb 接続を各実行コンポーネントで利用）。
  - SQLite は監視（monitoring.db）/ペーパートレード（paper_trading.db）用途で使用。
- research モジュール（factor_research.py）の基盤を追加
  - モメンタム等のファクター計算方針と定数を実装開始（関数 calc_momentum の導入、変数定義）。※実装は途中（ファイル末尾で切れている部分あり）。

Changed
- （このリリースは初期公開のため変更履歴はありません）

Fixed
- （このリリースは初期公開のため修正履歴はありません）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details / Known limitations
- .env 読み込み:
  - .env/.env.local の読み込み順は OS 環境変数を保護する仕様（.env.local は上書きだが OS 環境変数は保護）。
  - _parse_env_line はクォート・エスケープ・インラインコメント等に対応する比較的厳密な実装を行っているが、全ての .env 形式の差異に対応できない可能性あり。
- Logging:
  - コンソール出力は標準出力（stdout）を使用する。cron 等で stdout/stderr をリダイレクトする運用を想定。
- Execution / Monitoring:
  - 停止制御はファイルベース（data/stop_requested.flag / data/kill.flag）。KILL_FLAG_CLEAR_ON_START の設定に注意（本番で 1 にすると自動クリアされ危険）。
  - Monitoring は常に settings.sqlite_path（本番用監視 DB）を使用する仕様。
- Portfolio / Sizing:
  - position_sizing 内に「TODO」として price が欠損した場合のフォールバック（前日終値や取得原価の使用）や、将来的な銘柄個別 lot_size 対応が明記されている。現状は共通 lot_size（デフォルト 100）。
- research/factor_research.py:
  - ファクター計算モジュールの方針と定数は整備済み。関数実装は続きが必要（ファイル末尾が途中で切れている）。
- config/*.yaml の自動生成:
  - validate_config は config/*.yaml の存在を警告するが、スクリプト scripts/generate_config.py によりテンプレート生成を想定。
- 期待環境変数（一部）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定時は Settings._require により起動時例外。
  - PAPER_FILL_MODE 等の値検証あり。無効な値は起動時例外となる。

参考: 主なコマンド
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証:      python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動:   python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

以上。
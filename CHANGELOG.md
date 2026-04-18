CHANGELOG
=========

このファイルは Keep a Changelog 準拠の形式で、このコードベースで導入された主要な変更・機能を日本語でまとめたものです。

すべての重要な変更はここに記載します。

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db など）を使用し、MockBrokerClient を利用して本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内の data/stop_requested.flag により制御。
- 設定管理 / 検証 / ウィザード
  - config.py: 環境変数アクセス用 Settings クラスを追加。.env の自動読み込み（.env/.env.local の優先順位）と多数の設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 向け設定等）を提供。
  - validate_config.py: .env と config/*.yaml の起動前検証用 CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、パス検査、YAML パース（PyYAML 利用）などを行い、--strict オプションで警告を失敗扱いにできる。
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを追加。secret 項目のマスク表示、選択肢・デフォルト対応、.env 書き出し機能を備える。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を提供。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を追加。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元株丸め（lot_size）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りなどを実装。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次、30日保持）を一括設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を考慮。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。psutil ベースでアクセス権限エラー等を安全にハンドリング。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。閾値はソース内定義（例: uptime >= 99.0% など）。P95 算出ロジックを実装。
- データベース関連
  - 起動時に監視テーブルを保証する init_monitoring_db 呼び出しを run_execution/run_monitoring に追加（冪等）。
  - DuckDB 接続（分析用）と SQLite（監視/履歴用）を両方サポート。
- パッケージ管理
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログ出力の標準化: 全起動スクリプトは setup_logging を呼び出し、ログの出力とローテーションが統一されるようになった。
- .env 読み込みロジックの堅牢化:
  - export KEY=val 形式、クォート内のエスケープ、インラインコメントの取り扱いをサポート。
  - _load_env_file は override/protected オプションを使い OS 環境変数を保護しつつ .env.local を上書き可能にした。
  - プロジェクトルートの探索は .git または pyproject.toml を基準に上位ディレクトリから探索する実装に。

### Fixed
- プロセス優先度設定での例外を安全にログ・スキップするように改善（権限不足や未実装機能に対するフォールバック）。
- logging_setup: ログディレクトリ作成に失敗した場合でもコンソール出力が止まらないように修正。
- position_sizing: aggregate cap 適用時の端数処理で再現性を確保するため残差ソート（fractional remainder）を導入し、lot_size 単位で追加配分するロジックを実装。

### Documentation / UX
- 多くのモジュールに日本語ドキュメント文字列（docstring）を追加し、各関数の引数・戻り値・注意事項を明記。
- config_setup の対話ウィザードで既存 .env 読み込み、デフォルト提示、シークレットマスク表示、最終確認を追加。

### Internal / Tests
- validate_config で PyYAML が未インストールの場合に YAML 検証をスキップして警告するようにし、テスト環境での柔軟性を確保。

### Notes / Behavior
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数を読み取り、1 秒以上の正の整数でなければデフォルト（60 秒）にフォールバックする。0 以下や不正値は警告してデフォルトを使用。
- run_execution は起動時に停止フラグ（data/stop_requested.flag）が既に存在する場合は起動を中止し、実行中に検知すれば安全に停止を試みる。
- Settings.paper_fill_mode は有効値チェックを行い（instant/partial/never/reject）、不正な値で例外を送出する。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで .env の自動ロードを無効化できる（テスト向け）。

Security
--------
- 本リリースは機密情報（API トークン等）を .env に保存する設計であり、.env は Git にコミットしない旨を config_setup に明記。
- 実運用（KABUSYS_ENV=live）では LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険設定を validate_config が警告するようになっている。

Deprecated
----------
- なし

Removed
-------
- なし

Acknowledgements / References
-----------------------------
- 各モジュール内部の docstring（日本語）を参照してください。必要に応じて add-on の README やドキュメントを追記してください。
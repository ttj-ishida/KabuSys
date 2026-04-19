CHANGELOG
=========

すべての notable な変更は Keep a Changelog のガイドラインに従って記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- (今後のリリースに向けた変更をここに記載してください)

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリースを追加。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。
- 実行エントリ/ユーティリティ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番またはペーパートレード用の SQLite を選択し、BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動・停止管理（daemon スレッド）を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検出で安全に終了。
- 設定関連
  - config.py: 環境変数/ .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。PAPER_FILL_MODE 等の妥当性チェック、各種パス/閾値/環境フラグの accessor を提供。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（デフォルト値 / 選択肢・シークレット入力対応、.env の書き出し）。
  - validate_config.py: 起動前チェック CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml 存在チェック、--strict モード対応）。
- データベース / 分析
  - duckdb を統合し、分析用 DB パス（DUCKDB_PATH）サポート。
  - 監視用 SQLite（monitoring.db）初期化を行う init_monitoring_db 呼び出しを実行スクリプトに追加してテーブル整合性を保証。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights: 全スコア0 の場合に等金額へフォールバック) を実装。
  - portfolio/risk_adjustment.py: セクター集中上限チェック(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装。未知レジームは警告とともにフォールバック。
  - portfolio/position_sizing.py: 発注株数計算(calc_position_sizes) を実装（allocation_method: "risk_based"/"equal"/"score" 対応、lot_size 丸め、aggregate cap スケールダウン、cost_buffer サポート）。
  - portfolio/__init__.py で主要関数をエクスポート。
- 研究／分析用
  - research/factor_research.py（ファクター計算基盤）を追加（DuckDB 接続を受け取る設計、モメンタム/MA/ATR 等の計算を想定）。※ファイルの一部が存在（実装継続想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。uptime、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。閾値や日付フィルタオプションをサポート。
- ユーティリティ
  - utils/logging_setup.py: 全アプリ共通のロギング初期化ユーティリティを実装（stdout 用 StreamHandler、日次ローテーションの TimedRotatingFileHandler、ログディレクトリ作成のフォールバック処理、LOG_LEVEL/LOG_DIR の解決順）。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。Windows / POSIX を吸収し、アクセス権限不足等を安全にハンドリング。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし（初回リリース）

Notes / 実装上の注意
- .env 自動ロードはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config_setup により生成される .env は機密情報を含むため絶対にリポジトリにコミットしないでください（ファイルヘッダにも注意喚起を記載）。
- run_monitoring は「監視 DB（monitoring.db）は本番 sqlite_path を使用する」設計で、環境変数 KABUSYS_ENV に依存せず本番パスで監視データを記録します。一方、run_execution は paper_trading 環境時に paper_sqlite_path を使用して完全分離した DB に記録します。
- process_priority 周りは権限・プラットフォーム依存のため、設定に失敗した場合は警告を出して継続します。
- position_sizing の aggregate スケーリングや価格欠損時の振る舞いなど、将来的な拡張（銘柄別 lot_size、フォールバック価格の導入など）に備えた TODO コメントがあります。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出します。

Authors
- KabuSys チーム

License
- プロジェクトのライセンスに準拠してください（ソースツリーに LICENSE を含めることを推奨）。
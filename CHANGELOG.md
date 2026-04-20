# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

### Added
- ドキュメントおよびユーティリティの追加（config ウィザード、検証 CLI、レポートツール）。
  - 環境設定ウィザード: `kabusys.config_setup` により対話式で .env を作成・更新可能。
  - 設定検証 CLI: `kabusys.validate_config` で .env や config/*.yaml の事前チェックが可能。
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report` でペーパートレード DB からパフォーマンス/安定性レポートを生成。

### Changed
- ロギング設定ユーティリティを汎用化（`kabusys.utils.logging_setup`）。
  - stdout 出力と日次ローテートファイル出力（デフォルト logs/）をルートロガーに統一的に設定。
  - LOG_LEVEL / LOG_DIR の解決順を明示化。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして安全にフォールバック。

### Fixed
- 環境変数ロードの堅牢化（`kabusys.config`）。
  - .env の行パースで `export KEY=...`、クォート文字列、インラインコメント、エスケープを正しく扱うように実装。
  - OS 環境変数を保護する仕組み（.env 自動ロード時の protected set）を導入。

---

## [0.1.0] - 2026-04-20

初回リリース。

### Added
- 実行 / 監視用起動スクリプトを追加。
  - `kabusys.run_execution`:
    - ExecutionEngine の起動スクリプト。プロセス優先度を上げる (`set_process_priority("high")`)。
    - 環境に応じて Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / settings.paper_sqlite_path）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを作成。バックグラウンドスレッドで engine.run_session を実行し、停止フラグ検知で安全停止。
    - 実行中の PID 管理 (`data/execution.pid`)。
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計。
    - 外部停止フラグ（`data/stop_requested.flag`）の検知でループを終了。
- 設定管理（`kabusys.config`）。
  - プロジェクトルート自動検出（.git または pyproject.toml を検索）に基づき .env を自動読み込み（無効化可能）。
  - Settings クラスで各種設定値を集約（DB パス、API トークン、Paper Trading 設定、監視閾値など）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL の値検証。
- 環境設定ウィザード（`kabusys.config_setup`）。
  - 対話式で .env を生成/更新。既存値の再利用、シークレットマスク表示、保存前確認を実装。
- 設定検証ツール（`kabusys.validate_config`）。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML インストール時は）パース検証を実施。
  - `--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ユーティリティ（`kabusys.portfolio`）。
  - 候補選定・重み計算 (`select_candidates`, `calc_equal_weights`, `calc_score_weights`)。
  - セクター集中制限（`apply_sector_cap`）とレジーム乗数（`calc_regime_multiplier`）。
  - ポジションサイズ決定（`calc_position_sizes`）:
    - リスクベース / 等配分 / スコア加重方式に対応。
    - 単元株（lot_size）丸め、最大ポジション上限、総投入金額に対するスケールダウン（aggregate cap）を実装。
    - コストバッファ（手数料・スリッページ見積り）を考慮した計算。
- プロセス制御ユーティリティ（`kabusys.utils.process_priority`）。
  - Windows と POSIX を吸収する優先度設定。nice / HIGH_PRIORITY_CLASS へのマッピングと失敗時の警告。
  - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
- Logging セットアップユーティリティ（`kabusys.utils.logging_setup`）。
  - ルートロガーの再初期化（既存ハンドラの flush/close → 再設定）。
  - stdout を StreamHandler に使用（cron 等で stdout/stderr を統一するため）。
  - 日次ローテーションファイルハンドラ（30 日保持）。
- Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）。
  - ペーパートレード用 SQLite からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、Pass/Fail 判定（閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を出力。
  - 日付フィルタ（--from / --to）、DB パス上書き（--db）に対応。
  - P95 計算ユーティリティを実装（空データは N/A 扱い）。
- 研究用ファクター計算（`kabusys.research.factor_research`）の骨組み。
  - モメンタム、移動平均、ATR、流動性等の計算方針と定数を定義（DuckDB 接続を利用する設計）。

### Changed
- DB 連携
  - DuckDB と SQLite を両方サポートする設計を採用。Execution/Monitoring で DuckDB（分析用）と SQLite（監視・発注履歴）を併用。
- Paper Trading と本番の分離
  - Paper Trading 環境では専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を明示的に導入。
- エラーハンドリングとフォールバック
  - 各ユーティリティはリソース作成失敗時に安全にフォールバック（ログファイル作成失敗、プロセス優先度設定失敗など）するよう設計。

### Fixed
- .env パースの改善（`kabusys.config._parse_env_line`）。
  - export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント処理を正しく扱うように実装。
- モニタリングループの堅牢化（`kabusys.run_monitoring`）。
  - check_once() の例外をキャッチしてログに残し、次回ポーリングまで待機するように変更。
  - キーボード割り込み時のクリーンアップ（DB 接続のクローズ）を保証。

### Security
- .env は生成時に明示的に「絶対に Git にコミットしないこと」と注意文を挿入（`kabusys.config_setup`）。

---

開発・運用上の注意
- 本リリースのコマンドラインツール（config_setup / validate_config / tools）はローカル実行を想定しています。CI/CD 環境やコンテナ内での自動実行時は環境変数の扱いに注意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能）。
- Paper Trading 用 DB を誤って本番 DB に接続しないよう、環境変数と設定ファイルの管理を徹底してください。

---

（補足）バージョン番号はパッケージ内部の __version__ に基づき初回リリースを 0.1.0 として作成しました。コードベースのコメントや実装から読み取れる主要な機能と改修点を元に記載しています。
# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

- リリース日付の形式: YYYY-MM-DD
- 現行バージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-24

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。以下はコードベースから推測してまとめた主要な追加・改善点の一覧です。

### Added
- 基本ライブラリ / エントリポイント
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"` を定義。
  - 実行スクリプト:
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag による。監視は環境に関わらず production の sqlite_path を使用。
    - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を使用して本番 DB と分離。
  - CLI ユーティリティ:
    - config_setup: 対話式ウィザードで .env を生成・更新する機能（項目の説明、デフォルト、シークレット扱いなど）。
    - validate_config: .env および config/*.yaml の事前検証ツール（--strict モードで警告をエラー扱いにできる）。
    - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプト（期間指定可、P95 レイテンシ計算・稼働率・注文成功率等を判定）。
- 設定・環境管理
  - config.Settings クラスを実装。各種環境変数の取得とバリデーションを提供（J-Quants, kabu API, DB パス, PAPER_FILL_MODE の有効値検証など）。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env, .env.local を自動的に読み込み。OS 環境変数は保護され、必要に応じて上書き制御可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順制御、既存ハンドラのクリア処理、ファイルハンドラ作成失敗時のフォールバック対応を実装。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice を吸収）。CPU affinity 設定ユーティリティも提供。設定失敗時は警告ログを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank をタイブレークに並べる。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア総和が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 同一セクター集中上限（max_sector_pct）をチェックし、新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームはフォールバック 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based"、"equal"、"score"）に対応した株数算出。リスクベース（risk_pct, stop_loss_pct）や単元株丸め（lot_size）・1 銘柄上限・aggregate cap（available_cash に基づくスケールダウン）・cost_buffer（手数料/スリッページ見積り）を実装。スケーリング時は残差の大きい順に lot 単位で追加配分するロジックを搭載。
- データベース連携
  - DuckDB と SQLite を併用。duckdb は分析用（duckdb_path）、sqlite は監視・発注履歴用（sqlite_path / paper_sqlite_path）。run_monitoring と run_execution で接続を行い、init_monitoring_db を呼び出して監視テーブルの存在を保証。
- Paper Trading 検証レポート
  - tools/paper_verification_report: 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを算出して PASS/FAIL 判定する。P95 計算ユーティリティを実装。閾値（稼働率 99% など）を定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- エラーハンドリングの強化：
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合に例外情報をログ出力して次回ポーリングへ継続するように設計。
  - run_execution のスレッド管理で停止フラグ検出時に ExecutionEngine.stop() を呼びエンジンを停止させる安全な終了手順を実装。thread.join にタイムアウトを付与してデッドロックを回避。
- 環境変数パースの堅牢化（quoted values、export プレフィックス、コメント処理）。

### Security
- .env ファイルに関する注意喚起を config_setup で生成時に明記（.env を Git にコミットしない旨）。

### Notes / Behavioural details（重要）
- run_monitoring は「監視用途」のためどの実行環境でも settings.sqlite_path（本番監視 DB）を使用する仕様です。環境に応じて監視 DB を分離したい場合は設定（SQLITE_PATH）や実行スクリプトの修正が必要です。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用し、本番 DB と明確に分離されます。
- 環境変数の自動読み込み:
  - OS 環境変数は自動読み込み時に保護され、.env/.env.local の値で上書きされません（ただし .env.local は override=True として既存の値を上書きする挙動を持ちます。ただし protected により OS の値は守られます）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化できます（テスト等で便利）。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" で、不正値は ValueError を投げます。
- ログ出力はデフォルトで stdout と logs/<app_name>.log（日次ローテート、30日保持）に対して行われます。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後の改善案（コードから推測）:
- ファクター計算（research.factor_research）は実装途中の箇所があり、momentum 等の関数が未完了。DuckDB による処理の最適化や更なるファクター追加が想定されます。
- price の欠損（0.0）のフォールバック戦略や銘柄別 lot_size のサポートなど、実運用に即したフォールバック処理の追加。
- run_monitoring/run_execution のユニットテスト強化や起動/停止シーケンスの E2E テスト整備。

(以上)
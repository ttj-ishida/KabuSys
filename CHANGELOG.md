# Changelog

すべての非互換な変更はメジャー番号を上げること（Keep a Changelog 準拠）。

フォーマット:
- 「Added」「Changed」「Fixed」などのセクションで変更を分類しています。
- 日付は ISO 形式 (YYYY-MM-DD)。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

初回公開リリース。以下の主要コンポーネントを含みます。

### Added
- 全体
  - パッケージ初期版を追加。バージョン: 0.1.0（src/kabusys/__init__.py）。
  - Keep a Changelog に準拠した CHANGELOG を作成。

- 実行・監視関連
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を高く設定（set_process_priority）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、ExecutionEngine の起動・停止制御（stop flag / PID ファイルサポート）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能。
    - Monitoring は環境にかかわらず本番 sqlite_path を使う設計（注意点：意図的な動作）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了処理を実装。
    - 監視 DB の初期化（init_monitoring_db）と DuckDB 接続を行う。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込みルール（OS 環境変数を保護、.env.local は上書き可能）。
    - 複数の設定プロパティ提供（DB パス、LINE トークン、KABUSYS_ENV/LOG_LEVEL 検証、Paper Trading 関連設定など）。
    - PAPER_FILL_MODE の検証（有効値チェック）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - config_setup: .env 対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - 秘匿値のマスク、既存 .env 読み込み・Enter による現在値流用、.env ファイル書き出し（.env のテンプレートを生成）。
  - validate_config: 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス・config/*.yaml 存在・パース確認（PyYAML optional）、--strict モードをサポート。
    - 本番（live）用ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - シグナル選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み算出: calc_equal_weights（等金額）、calc_score_weights（スコア比率、全スコア 0 の場合は警告して等配分へフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限: apply_sector_cap（既存保有比率に基づき新規候補をフィルタ）。"unknown" セクターは制限適用対象外。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に対応。未知レジームは警告して 1.0 でフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - 株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元 (lot_size) 丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash を超えた場合のスケーリングと残差処理）を実装。
    - cost_buffer による保守的なコスト見積りをサポート。
    - TODO: 将来的な銘柄別 lot_size 拡張に関する注記あり。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR 解決順の実装、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - process_priority（src/kabusys/utils/process_priority.py）
    - cross-platform なプロセス優先度設定（Windows: priority class、POSIX: nice 値）。
    - CPU affinity の設定ユーティリティ（set_cpu_affinity）。
    - 権限不足や未対応 OS に対する警告ハンドリングを実装。

- ツール / レポート
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシなどを集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。 --db / 環境変数で上書き可能。
    - P95 計算や各種閾値（稼働率 99%、成功率 90% など）を定義。

- リサーチ
  - factor_research（src/kabusys/research/factor_research.py）
    - ファクター計算の設計と初期定義（モメンタム、Value、Volatility、Liquidity）の構成要素を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針を実装。
    - モメンタム関数 calc_momentum の実装を開始（定数・コメントあり）。※ 実装途中（下記 Known issues を参照）。

### Changed
- なし（初回リリースのため変更履歴なし）。

### Fixed
- なし（初回リリースのため修正履歴なし）。

### Known issues / Notes
- factor_research.calc_momentum 実装途中
  - ファイル末尾で関数の実装が途中（ソースに "start_da" で切れている）ため、現時点では完全なファクター計算が利用できません。リサーチモジュールは WIP（作業中）として扱ってください。
- run_monitoring の DB 選択仕様
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず settings.sqlite_path（本番用監視 DB）を使用します。開発/ペーパートレードと監視 DB を分離したい場合は実行方法・設定を見直してください。
- position_sizing の lot_size 拡張
  - 現行実装は全銘柄共通の lot_size を想定。個別単位の単元対応は TODO。
- 権限・環境依存の振る舞い
  - process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出してスキップします。
  - logging_setup はログディレクトリ作成に失敗するとファイル出力を無効化してコンソール出力のみで継続します。
- .env 自動読み込み
  - デフォルトでプロジェクトルートから .env/.env.local を自動でロードします。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Security
- 秘匿値は config_setup の対話ウィザードでマスクして入力を促すが、.env ファイルは絶対に Git にコミットしないようドキュメント注記があります。

---

今後の予定（例）
- factor_research.calc_momentum の完成とユニットテスト追加。
- portfolio の銘柄別 lot_size 対応。
- Execution/Monitoring コンポーネントの統合テストおよび CLI ドキュメント整備。

（この CHANGELOG はソースコードの現状から推測して作成しています。実際の変更履歴管理にはコミットログの利用を推奨します。）
# Changelog

すべての変更は Keep a Changelog の仕様に従って記載します。  
本ファイルはコードベースの現状から推測して作成した変更履歴です。

フォーマット:
- 変更は重要な点に絞って記載しています（実装の詳細や内部注釈は省略）。
- 日付は本ファイル作成日を使用しています。

※ 本リポジトリはバージョン情報として `kabusys.__version__ = "0.1.0"` を含んでいるため、初期リリースとして 0.1.0 を記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初期リリース。日本株自動売買システムのコア機能群を実装しました。主な追加項目は以下の通りです。

### Added
- 基本パッケージ基盤
  - パッケージエントリポイント `kabusys`、バージョン `0.1.0` を追加。
- 設定管理
  - `kabusys.config.Settings` 実装：
    - 環境変数／.env ファイルからの設定取得、検証機能を提供。
    - デフォルト値や型変換（Path, float, bool など）、環境（development/paper_trading/live）フラグ、paper_trading 用 DB パス等をサポート。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）を実装。
  - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。`.env` / `.env.local` 読み込みの優先度を実装。
  - `.env` パースの強化：
    - `export KEY=val` 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなど。
- 環境設定支援 CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで `.env` を初期作成・更新可能。シークレット項目のマスク表示、デフォルト値や選択肢をサポート。
- 設定検証 CLI
  - `kabusys.validate_config`:
    - .env と config/*.yaml の存在・基本整合性チェックを実行。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、--strict モードで警告を FAIL 扱いにする機能を実装。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出力。
- 実行（Execution）関連
  - 起動スクリプト `run_execution.py`:
    - `ExecutionEngine` 起動フローを提供（プロセス優先度設定、DB 接続、コンポーネント組み立て、スレッドでの実行監視）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を利用し、ペーパートレード専用 SQLite（デフォルト `data/paper_trading.db`）に完全分離して記録する設計。
    - PID ファイル (`data/execution.pid`) と停止フラグ (`data/stop_requested.flag`) を用いた起動/停止制御を提供。
    - RiskManager、OrderManager、Reconciler 等の組み立てサンプルを実装。RiskConfig のデフォルト値を設定。
- 監視（Monitoring）関連
  - 起動スクリプト `run_monitoring.py`:
    - `SystemMonitor` を定期ポーリングで呼び出す監視ループを実装。
    - 環境にかかわらず本番監視用 sqlite_path を使用する（monitoring 用 DB 初期化を保証）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグファイルによる安全停止処理を実装。
- データベース / 分析
  - DuckDB 統合ポイント（`duckdb.connect` の利用）を導入し、分析用 DB パス（`DUCKDB_PATH`）をサポート。
  - 監視 DB 初期化関数 `init_monitoring_db` を利用して起動時に監視テーブルの存在を保証。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でブレーク）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - `apply_sector_cap`：セクター集中制限（既存保有を考慮して新規候補を除外）、`unknown` セクターは制限対象外。
    - `calc_regime_multiplier`：市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング）を提供。未知レジームは警告のうえ 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`：allocation_method（risk_based / equal / score）に応じた株数決定ロジック、単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。cost_buffer による保守的見積りを考慮。
- ユーティリティ
  - ロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging`：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。ログディレクトリ作成の試行とフォールバックを実装。
    - LOG_LEVEL / LOG_DIR の解決順序を実装。
  - プロセス優先度・CPU アフィニティ `kabusys.utils.process_priority`：
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）と CPU affinity 固定機能を提供（psutil 依存）。権限不足や未サポート環境では警告を出して安全にスキップ。
- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポートを生成する CLI。SQLite (paper_trading) を参照し、稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。
    - デフォルトのしきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - 日付フィルタ（--from / --to）および DB パスの CLI 指定/環境変数対応を実装。
- 研究 / ファクター計算（実装着手）
  - `kabusys.research.factor_research`：DuckDB 経由でモメンタム等のファクターを計算するモジュールを用意（設計方針、定数、関数スケルトン含む）。価格テーブル（prices_daily）と財務テーブルを想定した設計。

### Changed
- （初期リリース：該当なし）

### Fixed
- （初期リリース：該当なし）

### Deprecated
- （初期リリース：該当なし）

### Removed
- （初期リリース：該当なし）

### Notes / Implementation details / Limitations
- config の自動読み込みはプロジェクトルート検出に依存するため、配布状況やファイル配置により自動ロードがスキップされることがあります。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `factor_research` は設計・計算ロジックの骨格を備えていますが、データスキャン範囲や一部計算の実装が継続開発対象であることを示唆しています（コードベースの途中実装を含む可能性）。
- `MONITOR_POLL_INTERVAL` 等の環境変数は不正値時にデフォルト値へフォールバックします（警告ログ出力）。
- `process_priority` / `set_cpu_affinity` は実行環境・権限に依存するため、失敗時は警告でスキップする安全設計です。
- Paper Trading と Live は DB を分離しているため、ペーパートレードデータは本番データベースに影響しません。

## Security
- シークレット（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は .env に直接保存される設計のため、`.env` を Git に含めない運用（README 等での注意喚起）を前提としています（`config_setup` にも同旨のコメントを記載）。
- ログレベルやログディレクトリ作成失敗などで機密情報が漏洩しないよう、ファイル書き込み失敗時にはコンソール出力にフォールバックします。

---

この CHANGELOG はコードから推測した「機能追加」「設計方針」「既知の制約」をまとめたものです。実際のリリースノートやユーザードキュメントを作成する際は、実際の仕様変更履歴・コミットログに基づいて補正してください。
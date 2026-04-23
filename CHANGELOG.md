# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
以下は提供されたコードベースの内容から推測して作成した変更履歴です（実際のコミット履歴ではなく、コードの機能・追加点を反映した要約となります）。

全体方針
- Semantic versioning に基づくバージョン管理を想定。
- 重要な追加・変更点をカテゴリ別に整理（Added / Changed / Fixed / Security / Removed / Deprecated）。

## [0.1.0] - 2026-04-23
初回リリース（コードベースに基づく機能束）

### Added
- アプリケーション基盤と起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検知で行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用 SQLite（data/paper_trading.db）で本番と分離して動作する。エンジンはスレッドで実行され、停止フラグ検出で安全に停止する。
- 設定管理
  - config.py: Settings クラスを実装し、環境変数／.env ファイルから設定を読み込む仕組みを提供。自動 .env ロードはプロジェクトルート検出に基づき行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パース機構は export 構文、クォート（エスケープ含む）、インラインコメント等に対応。
  - 各種設定プロパティ（J-Quants / kabu / LINE / DB パス / Paper Trading 設定 / 監視閾値 など）を提供。
- 設定補助ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。必須項目・任意項目を案内し、シークレット値はマスク表示。生成テンプレートを .env に書き込む機能を提供。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース検証（PyYAML が利用可能な場合）などを検証。--strict オプションで警告をエラー扱いにできる。
- 監視・メトリクス
  - monitoring_db 初期化関数を利用して監視テーブルの存在を保証（冪等化）。
  - run_monitoring と run_execution の両方で duckdb と sqlite 接続を確立し分析・監視データを扱う構成。
- ロギング／ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール（stdout）出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラクリアにより二重出力を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、権限や未対応 OS では警告を出してスキップする安全な実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）・等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score の配分方式、lot_size 丸め、aggregate cap スケーリング、cost_buffer を考慮した保守的見積り）。
- 研究用ファクター計算モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算（Momentum, Value, Volatility, Liquidity）を設計・部分実装。prices_daily / raw_financials を参照して (date, code) 単位で結果を返す設計。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成ツールを追加。指定期間の稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計して PASS/FAIL を判定する（閾値はソースコード内で定義）。--from/--to/--db オプションを提供。

### Changed
- ログ設定の標準出力先を stderr ではなく stdout に変更（utils/logging_setup.py）。cron / スケジューラ運用時のリダイレクト運用想定。
- .env の自動読み込みロジックは OS 環境変数を保護（protected set）し、.env.local を .env より優先して上書きする設計に（config.py）。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、配布後の動作が安定。
- run_execution.py: paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全に分離する動作を明確化。
- 監視と実行の両スクリプトでプロセス優先度を最初に high に設定する挙動を統一（utils/process_priority.set_process_priority を使用）。
- logging_setup: 既存ハンドラは flush/close してから削除する実装に変更し、二重設定やロガーの不整合を防止。

### Fixed
- ロギングの二重出力問題に対応（既存ハンドラを削除してから再設定）。
- .env パースにおけるクォート・エスケープ・コメントの取り扱いを強化（config._parse_env_line）。export プレフィックス対応、インラインコメント処理などでより堅牢に。
- run_execution 起動時に監視テーブルが存在しない場合のエラー対策として init_monitoring_db を呼び出し、監視テーブル存在を保証するように（init_monitoring_db は冪等）。
- process_priority 周りで権限不足や未対応プラットフォームでの例外を捕捉して警告を出し処理を継続するように（utils/process_priority.py）。
- position_sizing: 合計投資額が利用可能現金を超える場合のスケーリングと lot_size 単位での再配分ロジックを追加し、端数処理で一貫性を持たせた。

### Security
- .env ファイル生成テンプレートにはシークレット値（トークン / パスワード）を明示し、README 等へのコミット禁止注意を出力（config_setup._write_env）。

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

---

注記
- 本 CHANGELOG は提供されたソースコードから機能・動作を推測して作成しています。実際のコミットログやリリースノートとは差異がある可能性があります。必要であればコミット単位・変更差分を元により正確な CHANGELOG を生成できます。
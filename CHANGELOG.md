# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴です。

※ バージョン / 日付はコードベースの現状（__version__ = 0.1.0）と本日の日付を基に設定しています。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-04-19
初回公開リリース。システム全体の起動スクリプト、設定管理、ログ基盤、ポートフォリオ構築およびポジション計算、プロセス制御ユーティリティ、ペーパートレード検証ツール、ファクター計算モジュールなどの基本機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを `0.1.0` として公開。
  - CLI / スクリプト類のエントリポイントを追加（モジュール単体実行可能）。
- 設定管理
  - `kabusys.config`:
    - .env 自動ロード機能をプロジェクトルート（.git または pyproject.toml）から実行。
    - .env パースロジックを強化（`export` 前置、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等をサポート）。
    - 環境変数保護（OS環境変数を上書きしない挙動）と `.env.local` の上書きルールを実装。
    - `Settings` クラスを実装し、J-Quants / kabuAPI / DB パス / ログ設定 / 監視しきい値 などのプロパティを提供。
    - `PAPER_FILL_MODE` の検証（有効値: "instant","partial","never","reject"）。
    - `KABUSYS_ENV`、`LOG_LEVEL` 等の値検証。
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を初期生成・更新する機能を追加。シークレットはマスク表示し、入力補助・デフォルト値を提供。
    - .env のテンプレート出力（コメント付き）を実装。
  - `kabusys.validate_config`:
    - .env と config/*.yaml を起動前に検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML がある場合）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- 起動 / 実行スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを実装。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` 呼び出し）。
    - `paper_trading` 環境ではペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 依存コンポーネントの組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager（RiskConfig）、Reconciler, ExecutionEngine）。
    - ExecutionEngine をバックグラウンドスレッドで起動し、停止フラグ（data/stop_requested.flag）を検出したら安全に停止。
    - 実行時の PID 管理（`data/execution.pid` 等）。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境にかかわらず監視は監視用（本番）SQLite パスを使用する設計。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログに警告を出力。
    - 停止フラグ検出時にループを抜ける、`check_once()` 中の例外はログ出力して次のポーリングへ復帰。
- ロギング / プロセス制御
  - `kabusys.utils.logging_setup`:
    - ルートロガーの統一的設定ユーティリティを実装（StreamHandler -> stdout、TimedRotatingFileHandler 日次ローテート、30日保持）。
    - ログディレクトリ解決順（引数 > LOG_DIR > デフォルト "logs/"）と作成処理、作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice）設定を実装。
    - CPU affinity を最初 Nコアに固定する `set_cpu_affinity` を追加。
    - 権限不足時や未対応 OS では警告ログを出してスキップする安全実装。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（score 降順、tie-break に signal_rank）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター時価から上限超過セクターの新規候補を除外。`unknown` セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは警告のうえ 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - ポジションサイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer（手数料/スリッページ見積り）を考慮した保守的なコスト見積もりと、残余キャッシュによる端数処理で lot 単位で追加配分するアルゴリズムを導入。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`:
    - ペーパートレード用 SQLite を対象にレポートを生成する CLI を実装。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、閾値に基づいて PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - P95 計算関数と各種 SQL 集計クエリを実装。
- 研究 / ファクター計算
  - `kabusys.research.factor_research`:
    - DuckDB 接続を受け取りモメンタム等のファクター（mom_1m, mom_3m, mom_6m, ma200_dev など）を計算する設計を追加。営業日ベースの窓やスキャン日バッファ等を定義。
    - （注）モジュール内での実装は一部（ファイル末尾での計算ロジック）未完・継続的実装を想定。

### Changed
- ロギング関連の挙動を明確化：ログハンドラが既に設定されている場合は一旦削除して再設定（重複出力防止）。
- .env の読み込み優先度を明示（OS 環境変数 > .env.local > .env）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
- 監視プロセスは本番用 sqlite_path を使用するように仕様化（KABUSYS_ENV に依存しない）。

### Fixed
- .env のパースが不十分だった点を改善（引用符内エスケープ、export の前置、インラインコメントの扱いなど）。
- ログディレクトリ作成失敗やファイルハンドラ生成失敗時にプロセスがクラッシュしないように耐障害性を強化。コンソール出力のみで継続する設計に変更。
- プロセス優先度設定における権限エラーや未対応プラットフォームで例外が上がらないよう例外処理を追加し警告ログを出すように修正。

### Documentation / Usage notes
- CLI 起動例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレードレポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_FILL_MODE: instant / partial / never / reject
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB パス
  - SQLITE_PATH / DUCKDB_PATH / LOG_DIR / LOG_LEVEL
  - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- マイグレーション注意:
  - ペーパートレード時は DB が分離されるため、既存の monitoring DB とデータ共有が発生しない点に注意してください。
  - `KILL_FLAG_CLEAR_ON_START` を本番で誤って `1` にすると kill フラグが自動クリアされ、意図しない挙動につながるおそれがあります。

## 今後の予定（推測）
- research.factor_research の完全実装（SQL クエリ＋計算ロジックの完結）。
- Execution/Monitoring 周りの追加テスト、Broker クライアントの具象実装と本番連携テスト。
- strategy / data モジュールの追加と統合テスト。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリース履歴や日付、追加・修正の詳細は開発者の運用ポリシーに従って適宜更新してください。
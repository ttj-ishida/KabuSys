# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注意
- 本リリースはパッケージの初期公開（v0.1.0）に相当する内容を含みます。
- 環境変数やファイルパスのデフォルトはプロジェクトルート直下の `data/` / `logs/` 配下を想定しています。必要に応じて環境変数で上書きしてください。

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期機能を追加。
  - パッケージバージョン: `__version__ = "0.1.0"`
- 実行系・監視関連の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（既定: `data/paper_trading.db`）を利用することで本番DBと完全分離する設計。
    - 起動時にプロセス優先度を "high" に設定（psutil を利用）。
    - 停止フラグファイル (`data/stop_requested.flag`) を監視し、検知時に安全に停止する機構を実装。
    - 実行中はスレッドでエンジンを稼働させ、定期的に停止フラグを確認。
    - 起動時に PID ファイル（デフォルト `data/execution.pid`）を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし、警告ログを出力。
    - 監視は環境にかかわらず本番の SQLite パス（`SQLITE_PATH`）を使用する仕様。
    - 停止フラグ検知でループを終了。KeyboardInterrupt も扱う。
- 設定・環境管理機能を追加。
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出：.git または pyproject.toml を基準）。
    - `.env` / `.env.local` 読み込み順: OS 環境 > .env.local > .env。既定動作は自動読み込み有効（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env パース実装はクォートやエスケープ、`export KEY=val` 形式、インラインコメントなどに対応。
    - `Settings` クラスを提供し、必要な環境変数の取得とバリデーション（例: `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` の妥当性チェック）を行う。
    - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）、pid/kill flag パス、各種閾値（CPU/メモリ/ディスク）などを設定プロパティとして提供。
  - config_setup.py
    - 対話式ウィザードにより `.env` を新規作成・更新する CLI。既存値の再利用、シークレット入力（マスク表示）、選択肢提示などをサポート。
- 設定検証 CLI を追加。
  - validate_config.py
    - `.env` と `config/*.yaml` の簡易検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば実施）などを行う。
    - `--strict` オプションで警告を失敗扱いにできる（exit code 1）。
    - 本番環境 (`KABUSYS_ENV=live`) 向けの追加警告（LINE 通知未設定や Kill Switch の自動クリア設定など）。
- ロギング関連ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリは `LOG_DIR` または引数で指定可能。作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリーンアップして二重登録を防止。
- プロセス優先度 / CPU affinity ユーティリティを追加。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定（Windows/Linux/macOS 対応。psutil 利用）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS の場合はワーニングを出力して安全にスキップ。
- ポートフォリオ構築・サイズ計算関連モジュールを追加（純粋関数群、DB 参照なし）。
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、タイブレーク: signal_rank）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存保有を基にセクター別エクスポージャーを計算し上限超過セクターの候補除外）。
    - レジーム乗数（bull/neutral/bear に応じた乗数）を提供。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 発注株数計算（allocation_method: "risk_based" / "equal" / "score"）を実装。
    - 単元株（lot_size）、stop_loss、risk_pct、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）などを考慮。
    - aggregate cap 超過時にスケールダウンし、端数は残差ソートにより lot 単位で再配分するアルゴリズムを実装。
- Paper Trading 検証レポートツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト `data/paper_trading.db`）を読み込み、システム稼働率、注文成功率、送信率、API レイテンシ（平均、最大、P95）等の指標を計算してレポート出力。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - P95 計算、日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。
- 研究用ファクタ計算モジュール（骨格）を追加。
  - research/factor_research.py
    - DuckDB を使ったファクター計算（Momentum / Value / Volatility / Liquidity）を想定した設計。モメンタム計算関数 calc_momentum の実装開始（ファイル末尾で未完の箇所あり）。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Notes / Usage highlights
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- `PAPER_FILL_MODE` は "instant" | "partial" | "never" | "reject" のいずれかでなければならず、不正値は ValueError を投げます。
- run_monitoring は監視用 DB（`SQLITE_PATH`）を環境にかかわらず使用するよう設計されています。実行系 (run_execution) は paper 環境であれば別 DB を使い本番と分離します。
- ログは標準出力（stdout）にも出力されるため、cron やプロセスマネージャからの起動時にもログ取得が容易です。ファイル出力の失敗時は自動的にコンソールのみへフォールバックします。
- プロセス優先度や CPU affinity の設定は権限や OS の違いで失敗する可能性があります。該当時はワーニングを出力して無害にスキップします。

---
今後の予定（例）
- research/factor_research.py の未完実装（calc_momentum の続き）完了。
- ExecutionEngine / BrokerClient の実装詳細（実運用に向けた堅牢化とテスト）。
- config/*.yaml のテンプレート生成スクリプトやドキュメントの充実。
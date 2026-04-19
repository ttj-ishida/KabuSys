# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
なお、本リポジトリの初期バージョンはバージョン番号 0.1.0 としてリリースされています。

---

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初期リリース。主な追加機能、CLI、ユーティリティ、ポートフォリオ構築ロジック、実行/監視ランチャー、開発支援ツールなどを含みます。

### Added
- 一般
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - 環境変数・設定読み込みモジュール `kabusys.config` を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装。
    - .env/.env.local 自動読み込み（OS 環境変数を保護する仕組み、`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能）。
    - export KEY=val 形式や引用符付き値、インラインコメント等に対応した .env パーサ実装。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 / 環境種別 等のプロパティを安全に取得可能に。
    - Paper Trading 用 DB パス、PAPER_FILL_MODE 等のプロパティを追加。
- 設定支援 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘密値はマスク表示、オプション項目の空値扱い、.env を書き出すテンプレートを提供。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックなど。
    - `--strict` オプションで警告を失敗扱いにできる。
- 実行・監視ランチャー
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite を使用（本番 DB と分離）、BrokerClientFactory により MockBrokerClient の使用をサポート。
    - ExecutionEngine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立て、スレッドで実行。
    - 停止用フラグファイル（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
    - プロセス優先度を起動時に High に設定。
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する旨を明示。
    - 停止フラグの検知と例外耐性（check_once の例外はログ出力して継続）を実装。
- 監視・DB 初期化
  - `kabusys.monitoring.monitoring_db`（利用ファイル内参照）経由で監視テーブルの初期化を行う仕組みを導入（idempotent 初期化）。
- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 検証レポート生成スクリプトを追加。
    - SQLite データベースからシステム安定性（稼働率）、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計してレポート出力。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）に対応。
    - PASS/FAIL 判定の閾値をスクリプト内に定義（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：候補選定（スコア降順、signal_rank によるタイブレーク）、等重み・スコア加重の重み計算を実装。
  - `kabusys.portfolio.risk_adjustment`：セクター集中上限の適用（既存ポジション時価で判定）、レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - `kabusys.portfolio.position_sizing`：position sizing ロジックを実装。
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリングと残差処理（lot 単位での追加配分）を実装。
    - cost_buffer による保守的なコスト見積り、価格不足時のスキップなどの安全処理を含む。
- 研究モジュール（計算基盤）
  - `kabusys.research.factor_research`：モメンタム/ボラティリティ等のファクター計算基盤を追加（DuckDB 接続を受け、prices_daily/raw_financials を参照する設計、関数 calc_momentum 等の実装開始）。
- ユーティリティ
  - `kabusys.utils.logging_setup`：統一的ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - 既にハンドラがある場合は一度クリアして再設定（多重登録防止）。
    - LOG_DIR 作成失敗時はファイルハンドラをスキップしてコンソール出力で続行。
  - `kabusys.utils.process_priority`：プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）に対応し、未対応 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity 関数で CPU コア固定（psutil の cpu_affinity）をサポート（例外時は警告でスキップ）。
- パッケージのエクスポート
  - `kabusys.portfolio.__init__` による主要関数の公開。

### Changed
- （初期リリースのため該当なし）

### Fixed / Robustness
- .env 読み込み処理でファイルオープン失敗時に警告を出すようにして自動ロード失敗による致命エラーを回避。
- logging_setup:
  - ログディレクトリ作成失敗時のフォールバックを明示化（stderr に警告出力）。
  - ファイルハンドラ作成失敗時はコンソール出力のみで継続し、ログに警告を出すようにした。
- process_priority:
  - 未対応 OS や権限不足（psutil.AccessDenied 等）に対して安全にフォールバックする処理を実装。
- Paper verification report:
  - P95 計算およびレイテンシ欠損時の安全な N/A 表示を実装。

### Security
- .env 作成ウィザードのヘッダで .env を Git にコミットしないよう注意を記載（秘密情報の扱いに関する注意喚起）。

### Notes / Implementation details
- run_monitoring は監視用途のため KABUSYS_ENV にかかわらず本番の sqlite_path を参照する設計である点に注意。
- run_execution は paper_trading 環境時に専用の paper_trading.db を使用し、本番 DB と完全分離する方針。
- ポートフォリオ/position sizing の手数料・スリッページ見積りは cost_buffer で調整可能。将来的に銘柄毎の lot_size を取り扱う拡張を想定。
- research モジュールは DuckDB を利用し、外部 API に依存しない（prices_daily / raw_financials テーブル参照）方針。

---

発見された不具合や追加改善案は Issue にて管理してください。
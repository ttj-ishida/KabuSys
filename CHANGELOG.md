# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

- リリース日付形式: YYYY-MM-DD
- バージョン番号はパッケージ内の `kabusys.__version__` に合わせています。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワークの基本機能を提供します。主な追加点は以下の通りです。

### Added
- 基本パッケージ設定
  - `kabusys.config.Settings` — 環境変数／.env に基づく設定管理クラスを追加。
    - デフォルト値や妥当性チェックを含むプロパティ群（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。
    - `settings` シングルトンをエクスポート。

- .env 自動読み込み機能
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込み。
  - OS 環境変数は保護され、`.env.local` は既存値を上書きできる（ただし保護キーは上書きされない）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。

- 高度な .env パーサー
  - `export KEY=val` 形式のサポート。
  - シングル／ダブルクォート内のエスケープシーケンス処理、インラインコメントの取り扱い、無効行のスキップなどに対応。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を新規作成／更新する。
  - 各設定項目の説明、デフォルト、シークレットマスク表示、保存確認を実装。
  - 生成される `.env` のヘッダに警告（Git にコミットしないこと）を明示。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に必須環境変数やパス、YAML 設定ファイル等を検証するツールを追加。
  - `--strict` オプションで警告を失敗扱いにできる。
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。

- 実行・監視起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は paper-trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理（PID ファイル、停止フラグの監視）を実装。
    - デフォルトのリスク設定（例: max_position_pct=0.20, max_utilization=0.80 など）を組み込み。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に関わらず本番の `sqlite_path` を使用する設計（監視データは一元管理）。

- 監視 DB 初期化ユーティリティ呼び出し
  - `init_monitoring_db` を使用して起動時に監視テーブルの存在を保証（冪等）。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。
    - ログレベルとログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を提供。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`：
    - クロスプラットフォームでプロセス優先度を設定（Windows / POSIX 対応）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - アクセス権限不足などの失敗時は警告ログでフォールバック。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（スコア降順 + タイブレーク）`select_candidates`
    - 等配分 `calc_equal_weights`
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限 `apply_sector_cap`（既存保有を考慮して当日の新規候補を除外）
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear マップ、未知レジームはフォールバック）
  - `kabusys.portfolio.position_sizing`：
    - position sizing ロジック `calc_position_sizes`（risk_based / equal / score に対応）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、残差処理（lot 単位での再配分）を実装
    - cost_buffer による保守的なコスト見積りを考慮

- 研究用ファクター計算モジュール
  - `kabusys.research.factor_research`：
    - モメンタム等ファクター計算の骨格（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - 主要定数（期間定義）や `calc_momentum` のインターフェースを追加（実装の一部）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から集計を行い、稼働率、注文成功率、送信率、API レイテンシ（P95）等を算出して PASS/FAIL 判定を出力。
    - デフォルト閾値:
      - 稼働率 (uptime) >= 99.0%
      - 注文成立率 (fill_rate) >= 90.0%
      - 送信率 (send_rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数 `--from` / `--to` / `--db` に対応。

### Changed
- N/A（初回リリースのため既存変更はありません）。

### Fixed / Robustness
- .env 読み込みでファイルオープン失敗時に警告を出して処理を継続するように改善（例外ハンドリング追加）。
- ログディレクトリ作成失敗やファイルハンドラ作成エラー時にフォールバックしてプロセスを継続するように変更（起動失敗を回避）。
- `MONITOR_POLL_INTERVAL` の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、警告ログを出力するように実装。

### Security / Operational notes
- `.env` は絶対にリポジトリへコミットしないことを README／生成ヘッダで明示。
- 本番（KABUSYS_ENV=live）向けチェックを `validate_config` に追加。LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な値（1）などの注意喚起を行う。
- 監視・実行プロセスはファイルベースの停止フラグ（data/stop_requested.flag 等）および PID ファイルを用いた停止制御を採用。

---

将来的な改善候補（メモ）
- prices_daily や raw_financials によるファクター計算の追加拡張（factor_research の完成）。
- lot_size を銘柄毎に持たせるための stocks マスタとインターフェース拡張。
- position sizing の手数料・スリッページモデルをより詳細に導入。
- Monitoring / Execution の Docker / systemd 向けユニットファイルやデプロイ手順のドキュメント化。

もしこの CHANGELOG に追加したい詳細や、リリース日付の変更、あるいは「Unreleased」セクションを設けたい場合は指示してください。
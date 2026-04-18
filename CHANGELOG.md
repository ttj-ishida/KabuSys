# Changelog

すべての重要な変更点はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
意味のある変更はすべてバージョンごとに記載してください。

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 全体
  - パッケージの初期バージョンを追加。パッケージメタデータは `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト
  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 `sqlite_path` を使用。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 予期しない例外はロギングし、次のポーリングまで待機して継続する。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは Paper Trading 用の専用 SQLite（`data/paper_trading.db`）を利用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグファイル検知によりエンジンを安全に停止。
- 設定・環境
  - `kabusys.config`:
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード機能を追加（`.env` と `.env.local` の順、OS 環境変数は保護）。
    - `.env` の行パーサを実装し、`export KEY=val`、シングル/ダブルクォート、エスケープ、コメント処理に対応。
    - `Settings` クラスで各種設定プロパティを提供（J-Quants / kabuAPI / DB パス / paper_trading 切替 / 監視閾値 等）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant", "partial", "never", "reject"）と `paper_sqlite_path` のサポート。
  - config_setup: 対話式の .env 作成/更新ウィザードを実装。シークレットのマスク表示、選択肢・デフォルト表示、保存機能を提供。
  - validate_config: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パス/config YAML 存在チェック、live 環境用の警告等）。`--strict` オプションで警告も失敗扱いに。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を統一的に設定するユーティリティを追加。
    - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト "INFO" の順に解決。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。
  - utils.process_priority:
    - プラットフォーム差異を吸収する `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応し、権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構成ライブラリ（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + tie-break による候補選定。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分。スコア合計が 0 の場合は等重でフォールバック（警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数の配分方式（"risk_based", "equal", "score"）に対応した発注株数算出を実装。lot_size（単元）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積り、残余キャッシュでの再配分ロジックを提供。
- モニタリング DB 初期化
  - `init_monitoring_db` を参照するフローが起動スクリプトに組み込まれ、監視用テーブルが存在しない場合に初期化（冪等処理）するように。
- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト `data/paper_trading.db`）から指標を集計する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）、リスク却下数 等。
    - デフォルトの合否基準（閾値）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 期間フィルタ（--from / --to）対応、結果の PASS/FAIL 表示。
- 研究モジュール（開始）
  - research.factor_research: DuckDB 接続を受けるファクター計算モジュールの骨組みを追加（モメンタム等の計算方針と定数を定義）。calc_momentum の実装開始（ファイル末尾で途切れあり、今後拡張予定）。

### Changed
- 環境変数の自動ロード
  - 自動ロード時に OS 環境変数を上書きしない（`.env.local` は override=True だが既存 OS 環境変数は protected として上書きを避ける）。
- ログ出力のデフォルト挙動
  - コンソールログは stderr ではなく stdout に出力するように仕様決定（Task Scheduler / cron 等の運用を想定した一本化）。

### Fixed
- .env パースの堅牢化
  - クォート内のエスケープ処理やインラインコメント、`export` プレフィックスの扱いを改善し、より現実的な .env 形式を正しく処理できるように修正。
- process priority に関する例外処理強化
  - 権限不足や未実装の API でも落ちないようにキャッチして警告ログを出すように変更。

### Security
- .env の取り扱いに関して
  - config_setup により .env を対話的に作成する際にファイルヘッダーで「.env を絶対に Git にコミットしないこと」を明記し、シークレットをマスクして表示するようにした。

### Notes / TODO
- research.factor_research.calc_momentum の実装は途中で切れているため、ファクター計算は今後のリリースで完成予定。
- position_sizing の price 欠損処理（price=0 の扱い）に関する TODO コメントあり。将来的に前日終値や原価フォールバックを検討する予定。
- 一部 CLI やユーティリティは外部ライブラリ（psutil, duckdb, PyYAML 等）への依存があるため、運用環境でのインストールを確認してください（validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出します）。

---

（以降のバージョンでは、変更点をセクションごとに分けて記載してください: Added / Changed / Deprecated / Removed / Fixed / Security）
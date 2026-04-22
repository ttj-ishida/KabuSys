# CHANGELOG

すべての重要な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

※ 本 CHANGELOG は与えられたソースコードから実装内容を推測して作成しています。実際のコミット履歴ではなく、機能・修正点の要約です。

## [Unreleased]

- ドキュメント化や小さなリファクタリング、テスト追加等の小変更に対応するための準備。

---

## [0.1.0] - 2026-04-22

初回リリース想定。自動売買システム「KabuSys」のコア機能群を実装。

### Added
- 基本パッケージとバージョン情報
  - パッケージメタデータ: `kabusys.__version__ = "0.1.0"` を定義。

- 環境設定管理
  - Settings クラス（`kabusys.config`）を実装。環境変数をラップしてアプリ設定を提供。
  - .env 自動読み込み機能を実装:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` / `.env.local` を読み込む。OS 環境変数の上書きは制御可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは次をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - インラインコメントの扱い（クォートなしでは '#' の直前がスペース/タブのときにコメントと判断）
  - 必須環境変数取得ヘルパ `_require` を提供（未設定時は ValueError を発生）。

- 設定作成ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。
  - `.env` の初期作成 / 更新を支援。秘密値はマスク表示。生成テンプレートを `.env` に保存。

- 設定検証 CLI
  - `kabusys.validate_config` 実装。環境変数、DB パス、config/*.yaml の存在と YAML のパースを検証。
  - `--strict` オプションで警告も失敗扱いにできる。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout への StreamHandler（標準出力）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数でロギングを柔軟に制御。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority` を実装。Windows と POSIX を吸収してプロセスの優先度（high/normal/low）を設定。
  - `set_cpu_affinity` を実装し、必要に応じてプロセスを先頭 N コアにピン留め可能。
  - psutil の権限や未対応 OS を考慮して安全にフォールバック。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py`:
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて本番または paper_trading 用の SQLite を使い分け（paper_trading は独立した `data/paper_trading.db` を使用）。
    - BrokerClientFactory を経由してブローカークライアントを生成（paper_trading では MockBrokerClient を用いる想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）や pid ファイルを取り扱い、優雅に停止。
  - 監視（モニタリング）ループ起動スクリプト `run_monitoring.py`:
    - プロセス優先度を "high" に設定。
    - 監視 DB は環境に依らず本番 sqlite_path を使用（監視は本番 DB を参照する仕様）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - stop flag を検知してループを終了。例外発生時はログに例外情報を出力して次のポーリングへ継続。

- データベース統合
  - DuckDB 接続（`duckdb.connect`）を導入して分析用 DB を扱う（`Settings.duckdb_path`）。
  - SQLite は監視・発注履歴用に使用（`Settings.sqlite_path` / `Settings.paper_sqlite_path`）。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（score 降順・signal_rank による tiebreak）。
    - 等重み・スコア重みの重み計算（スコアが全て 0 の場合は警告を出して等重配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター比率が閾値を超えると新規候補を除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数決定ロジック（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に収まるようスケーリング）、cost_buffer を考慮。
    - スケールダウン時の端数分配ロジック（残余キャッシュで fractional remainder が大きい銘柄から lot 単位で追加）。

- 研究用ファクター計算
  - `kabusys.research.factor_research` の骨格を実装（モメンタムや MA200、ATR、ボリューム系の計算を想定）。DuckDB の prices_daily / raw_financials を利用する設計。※ ファイル末尾で計算処理（calc_momentum 等）の実装が途中まで含まれている（大枠実装あり）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` 環境変数またはデフォルト `data/paper_trading.db`）からデータを集計してレポートを標準出力へ出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下回数など。
    - 閾値による PASS/FAIL 判定を実装（稼働率 99% など）。P95 計算や NULL（データなし）に対する扱いあり。
    - CLI オプション: --from / --to / --db をサポート。

### Changed
- N/A（初版のため既存からの変更点は無し。ただし実装は安全性・冗長性を考慮して設計されている点を明記）
  - 各所で「デフォルト」や「フォールバック」を明確に実装（例: MONITOR_POLL_INTERVAL の不正値処理、ログディレクトリ作成失敗時のフォールバックなど）。

### Fixed
- N/A（初版）

### Deprecated
- N/A

### Removed
- N/A

### Security
- 環境変数の秘密情報は `.env` 作成ウィザードでマスクして表示。`.env` をコミットしないようテンプレートに注意書きを追加。

---

## マイグレーション / 運用上の注意

- .env の自動読み込み
  - デフォルトで `.env` / `.env.local` が自動読み込みされます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は保護され、`.env` に同名キーがあっても通常は上書きされません（`.env.local` は override=True で上書き可。ただし OS 環境変数は protected）。

- 環境変数の検証
  - `python -m kabusys.validate_config` で起動前に必須設定の確認を推奨。
  - `--strict` を付けると警告も失敗扱いになります（CI でのチェックに有用）。

- Paper Trading と本番 DB の分離
  - paper_trading 実行時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、本番の `SQLITE_PATH`（例: `data/monitoring.db`）とは完全に分離されます。運用時は誤操作で本番 DB に接続しないよう `KABUSYS_ENV` を適切に設定してください。

- ログ
  - デフォルトは `logs/` に日次ローテートでログファイルを出力します。LOG_DIR 環境変数で変更可能。ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を "high" にセットしようとします。権限不足で失敗した場合は警告ログのみで継続します。

- 停止フラグ / PID 管理
  - 停止はプロジェクトルート下の `data/stop_requested.flag`（及び pid ファイル paths）により管理します。運用での停止/再起動手順を事前に定義してください。

---

もし特定のファイルや機能（例: factor_research の続き実装、ExecutionEngine の詳細、Broker の Mock 実装など）についてより詳細な変更履歴やドキュメント化を希望される場合は、そのファイル群または想定する差分（追加/修正点）を教えてください。さらに正確な CHANGELOG（コミット単位や日付付き）を生成できます。
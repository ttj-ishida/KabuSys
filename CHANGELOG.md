# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回公開リリース。本バージョンでは自動売買システム「KabuSys」のコア機能群、運用用ユーティリティ、設定管理、検証ツール、ポートフォリオ構築ロジックなどを実装しています。

### Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理 / 初期化
  - `kabusys.config`:
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装。CWD に依存しない自動 .env ロードを実現。
    - 高機能な .env パーサを実装（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮）。
    - `.env` 自動ロードの抑制用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - `Settings` クラスを提供し、環境変数の取得と検証をプロパティとして統一。J-Quants / kabuステーション / DB パス / Paper Trading 関連 / 監視閾値 等の設定をカバー。
    - `PAPER_FILL_MODE` の有効値チェック（"instant"|"partial"|"never"|"reject"）などのバリデーションを実装。
    - Paper Trading 用 DB パス（`paper_sqlite_path`）と運用環境判定プロパティ（`is_live`, `is_paper`, `is_dev`）。

- 対話式設定ウィザード
  - `kabusys.config_setup`:
    - .env の対話式作成・更新ウィザード。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 通知設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）をサポート。
    - 既存 .env 読み込み、シークレットのマスク表示、保存時の確認、.env ファイル書き出しロジックを提供。

- 設定検証 CLI
  - `kabusys.validate_config`:
    - 起動前に .env と config/*.yaml の検証を実行する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パース検証（PyYAML 有無を考慮）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`:
    - 全起動スクリプトで統一して使用可能なロギング設定ユーティリティを提供。
    - stdout 出力用 StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ解決順とログレベル解決順をサポート。
    - ログディレクトリ作成失敗時にはファイル出力をスキップして console のみで継続するフェイルセーフを実装。
  - `kabusys.utils.process_priority`:
    - Windows と POSIX（Linux/Mac/FreeBSD）で差異を吸収するプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を提供。権限不足など失敗時は警告ログでフォールバック。

- 実行系 / 監視スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプト。プロセス優先度を高に設定し、Broker クライアントをファクトリから構築。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は専用 SQLite（data/paper_trading.db デフォルト）へ記録して本番 DB と分離。
    - OrderRepository、OrderManager、RiskManager（デフォルト設定を含む）、Reconciler を組み立て、ExecutionEngine をスレッドで実行。pid ファイル、停止フラグ(stop_requested.flag) による安全停止処理を実装。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう明示。
    - 停止フラグ検出・例外ハンドリング・リソースクローズを実装。

- 監視 DB 初期化
  - 監視用 DB 初期化用関数 `init_monitoring_db` を利用して起動時に監視テーブルが存在することを保証（冪等な初期化）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、タイブレークに signal_rank を採用）、等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（スコア合計が 0 の場合に等金額へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`：同一セクターの既存保有が閾値を超える場合に新規候補を除外。unknown セクターは上限適用外にする挙動。
    - `calc_regime_multiplier`：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームでは警告を出して 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`：allocation_method に応じた株数決定（"risk_based" / "equal" / "score"）を実装。損切り率・単元株丸め（lot_size）・1銘柄上限（max_position_pct）・合計投下上限（max_utilization）・手数料スリッページ見積り（cost_buffer）を考慮したスケーリングロジックを実装。合計が利用可能現金を超えた場合のスケールダウンと残余キャッシュに基づく再配分ロジックを実装。

- 研究用ファクター計算（着手）
  - `kabusys.research.factor_research`:
    - モメンタム等のファクター計算基盤を実装。DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照してモメンタム・MA200乖離・ATR・出来高等を算出する設計（calc_momentum の実装開始）。（注: ファイル末尾が未完の箇所あり、今後拡張予定）

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成ツール。SQLite（Paper Trading DB）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、所定の閾値に基づいて PASS/FAIL 判定を出力する CLI を提供。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）対応、DB 存在チェック、各クエリは例外発生時に安全に N/A を返す実装。

### Changed
- 初回リリースにあたり多数の新規機能を追加したため、既存コードの互換保持や後方互換仕様はリリース方針として後続で細かく調整予定。

### Fixed
- ログ設定周りでログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール（stdout）出力のみで動作を継続するフェイルセーフを実装。
- 環境変数読み込み時にファイル読み込み失敗が起きた場合、警告を出して処理を継続するように変更（テスト環境や権限問題での起動性向上）。
- プロセス優先度設定 / CPU affinity 設定で権限不足や未対応プラットフォームの例外に対して警告ログでフォールバックするようにして、起動時の致命的エラーを回避。

### Security
- 本リリースでは特にセキュリティ脆弱性は報告されていませんが、`.env` に機密情報（API トークン・パスワード）を保存する設計のため、`.env` の Git 追跡禁止を README 等で明示する必要があります（config_setup にも注記あり）。

### Notes / 既知の制限
- `research/factor_research.py` の一部（ファイル末尾）が未完の箇所があります。今後のリリースでファクター計算ロジックを完成させます。
- 一部の外部依存（例: PyYAML, psutil, duckdb, sqlite3, J-Quants/kabu API クライアント等）は環境に依存します。validate_config は PyYAML の有無に応じて YAML 検証をスキップします。
- Paper Trading と本番 DB の完全分離（デフォルト設定）は実装済みですが、運用時は .env（PAPER_TRADING_SQLITE_PATH 等）の設定を確認してください。
- `PAPER_FILL_MODE` など、環境変数値の検証によって不正値は起動時に例外となるため、`config_setup` と `validate_config` を利用して事前にチェックすることを推奨します。

---

作者・保守者: KabuSys 開発チーム  
（ドキュメントや追加の変更はリポジトリの Issue / PR にて管理してください）
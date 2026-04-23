# Changelog

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

以下は、提示されたコードベースから推測して作成した変更履歴です。

## [Unreleased]

- なし（初回リリース相当の内容は v0.1.0 に含まれます）

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行用スクリプト / エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。ブローカークライアントのファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、スレッドでエンジンを実行。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番DBと分離。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル管理（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番用 `sqlite_path` を使用する（監視テーブルの初期化を行う）。

- 設定管理・初期化ツール
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
    - `.env` と `.env.local` の読み込み順序、OS 環境変数の保護（上書き防止）を実装。
    - `Settings` クラスを提供し、J-Quants / kabu / DB / 監視閾値 / 環境種別などの設定アクセスを統一。
    - `paper_fill_mode`, `paper_sqlite_path` などペーパートレード関連設定を追加。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。主要な設定項目の質問・デフォルト・マスク（シークレット）対応、ファイル出力機能を実装。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスや config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告をエラー扱いにする機能を追加。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的な logging セットアップ関数 `setup_logging()` を追加。stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ出力先を制御可能。既存ハンドラのクリア処理やファイルハンドラ作成失敗時のフォールバックを実装。

  - utils/process_priority.py
    - Windows/Linux/macOS におけるプロセス優先度（および CPU affinity）設定ユーティリティを追加。`set_process_priority()` と `set_cpu_affinity()` を提供。
    - 権限不足や未サポート環境での例外を警告に変換して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順）、等重配分、スコア正規化配分を実装（score が全て 0 の場合は等重にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position size（発注株数）算出ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いた保守的見積りなどをサポート。

- 研究 / ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、流動性などを想定）。設計方針・定数を定義（未完の関数も含む）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を検証する報告書生成スクリプトを追加。SQLite のペーパートレード DB を読み込み、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（しきい値はソース中に定義）を行う。
    - コマンドライン引数で日付範囲（--from / --to）や DB パス（--db）を指定可能。

- DB 関連
  - monitoring/monitoring_db モジュールによる監視テーブル初期化呼び出しを run_* スクリプトから行うように統合（冪等性確保）。

### Changed
- なし（初回リリース相当のため、破壊的変更はなしと想定）

### Fixed
- なし（明示的なバグ修正履歴はソースからは判定できず）

### Security
- 環境変数読み込みの際、システムの既存環境変数を保護する仕組み（protected set）を導入。`.env` を誤って上書きしないデフォルト挙動を採用。

### Notes / Migration
- 環境変数自動読み込み
  - プロジェクトルートが検出できる場合、起動時に `.env`（デフォルト）を自動ロードし、`.env.local` は `.env` の上書きとしてロードされます。OS 環境変数はデフォルトで上書きされません。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - PAPER_FILL_MODE（instant / partial / never / reject）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
  - SQLITE_PATH（監視 DB）
  - DUCKDB_PATH（分析用 DB）
  - LOG_LEVEL / LOG_DIR
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）

- ペーパートレード分離
  - Execution エンジンは `KABUSYS_ENV=paper_trading` 時にペーパートレード専用 DB を使用するため、本番データと完全分離されます。

- 起動・運用
  - run_monitoring / run_execution は停止フラグ（data/stop_requested.flag）で外部から停止できます。実行中は PID ファイル / 停止フラグにより安全に管理する設計です。
  - 起動時にプロセス優先度を "high" に設定し、ログは stdout と日次ローテーションされるファイルに記録されます（logs/<app_name>.log）。

- ログ
  - 既存ハンドラを一旦クリアしてから新しいハンドラを設定するため、多重設定による重複ログ出力を防止します。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

- ポートフォリオ構築
  - position sizing では単元株（lot_size=100 を想定）での丸めや、利用可能現金に応じたスケーリングを行うため、実際の発注株数は重み計算結果から調整されます。

---

（注）上記は提供されたソースコードの内容から推測した変更点・機能一覧です。実際のコミット履歴や差分ログがある場合はそれに基づく正確な CHANGELOG を作成することを推奨します。必要であれば、より詳細な項目分け（小さな実装単位ごとの変更履歴）や将来のリリース計画用テンプレートを作成します。
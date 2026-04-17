# CHANGELOG

すべての注目すべき変更点を記録します。
このファイルは Keep a Changelog の慣習に従います。  

注: リリース日には、このスナップショットの作成日 (2026-04-17) を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys コアモジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 環境設定 / 設定管理
  - Settings クラスを実装。環境変数から各種設定を提供（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など）。
  - paper_trading 用の分離された SQLite パス (`PAPER_TRADING_SQLITE_PATH`) と `paper_fill_mode` の検証を実装（有効値: "instant" | "partial" | "never" | "reject"）。
  - 環境自動読み込み機能を追加: プロジェクトルートの `.env` と `.env.local` を自動で読み込み（OS 環境変数を保護、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - `.env` パーサを強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱い等に対応。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成 / 更新するツールを追加。
  - デフォルトや説明付きの入力、シークレット値のマスク表示、保存確認機能を実装。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に必須環境変数や config/*.yaml の存在・パースを検証する CLI を追加。
  - `--strict` オプションで警告を失敗扱いにできる。
  - 本番環境向けのガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を追加。

- 実行 / 監視起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Mock ブローカーを使用し、paper_trading 用 DB に完全分離して記録。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル管理を実装。
    - ExecutionEngine の組み立てに必要な OrderRepository、OrderManager、RiskManager、Reconciler の初期化を行う。
    - RiskManager のデフォルト設定（max_position_pct 等）と、初期ポートフォリオ値をブローカーから取得して設定するフローを実装。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず production 用 `sqlite_path` を使用する（監視 DB の分離設計）。
    - 停止フラグ検知でループ終了、check_once 実行時の例外をログに残して続行する実装。

- モニタリング DB 初期化ユーティリティ
  - 監視関連テーブルが存在することを保証する `init_monitoring_db` 呼び出しの導入（冪等に呼べる設計）。

- ポートフォリオ構築ロジック（純粋関数）
  - portfolio_builder:
    - select_candidates: スコア降順で候補を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ。sell_codes（当日売却候補）をエクスポージャ計算から除外可能。
    - calc_regime_multiplier: 市場レジーム ("bull", "neutral", "bear") に応じた投下資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数算出を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余分配アルゴリズムを含む詳細ロジックを実装。

- 研究用ファクター計算
  - research/factor_research.py:
    - DuckDB 接続を前提に momentum（1M/3M/6M、MA200乖離）、volatility（ATR20 等）等のファクターを計算する関数を追加。
    - データ不足時の None 返却やウィンドウ行数チェック等に対応。
    - DuckDB を利用した SQL ベースの実装でスケーラブルに集計。

- ユーティリティ
  - process_priority:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
    - Windows / POSIX (Linux/macOS/FreeBSD) 間で差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップする堅牢な実装。
    - Windows 用優先度定数は psutil の存在する定数を getattr で取得してフォールバック。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite DB を解析して検証レポートを生成（稼働率、注文成功率、送信率、P95 レイテンシ等）。
    - 閾値定義（稼働率 >= 99%、注文成功率 >= 90% 等）と Pass/Fail 判定を実装。
    - 日付フィルタ、P95 算出、欠損時の N/A 表示などの出力フォーマットを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env ファイルの生成時に注意喚起を追加（.env を Git にコミットしない旨のコメントをヘッダに記載）。

Notes
- データベースやファイルパスのデフォルトは project_root に対する相対パス（例: data/monitoring.db, data/kabusys.duckdb 等）。`validate_config` で親ディレクトリ存在チェックを行い、起動時に自動作成される場合がある旨を警告する。
- 実行スクリプトは停止フラグ（data/stop_requested.flag 等）と pid ファイルを用いた制御を行う仕様です。運用時はこれらのファイルの扱いに注意してください。

(以降のリリースでは、既知の改善予定：価格欠損時のフォールバック、銘柄ごとの単元対応、さらに細かなログ／監視項目の追加などを予定しています。)
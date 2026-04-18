# CHANGELOG

すべての注目すべき変更をここに記録します。これは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更（未リリース）
- 各リリース: 日付付きで主要な追加・変更・修正を列挙

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初期リリース。KabuSys のコア機能群を実装しました（設定管理、実行/監視スクリプト、ポートフォリオ構築、ユーティリティ、ツール、リサーチ）。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - プロジェクト構成に基づく自動 .env ロード機能を実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
  - OS 環境変数を保護する .env 読み込みロジック（`.env` と `.env.local` の読み込み順、`.env.local` は上書き）。
  - 環境変数パーサの強化: export 形式、クォート内のバックスラッシュエスケープ、行内コメント処理に対応。

- 設定関連
  - Settings クラスによる環境変数ラッパを追加。J-Quants / kabuAPI / LINE / DB / 監視閾値 等のプロパティを提供。
  - `config_setup.py`: 対話式ウィザードで `.env` を初期作成・更新する CLI を実装（シークレット入力マスク、デフォルト値、選択肢、保存確認）。
  - `validate_config.py`: 起動前に必須環境変数や config/*.yaml 等を検証する CLI を追加。`--strict` オプションで警告を FAIL 扱いに可能。

- 実行・監視
  - `run_execution.py`: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて Paper Trading 用 DB を分離（`data/paper_trading.db`）し、Mock ブローカーを使用可能。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理と PID ファイル管理。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知でエンジン停止・スレッド終了を待機。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、不正値はフォールバックして警告）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知、例外キャッチでループ継続、KeyboardInterrupt による終了処理を実装。

- データベース / 分析
  - DuckDB 接続サポート（`duckdb` を利用）を導入。設定経由でパスを指定可能（`DUCKDB_PATH`）。
  - 監視用 SQLite 初期化ユーティリティ呼び出しを実装（監視テーブルの冪等初期化）。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`:
    - 候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックし警告を出力。
  - `portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" をサポート。未知レジームはフォールバック。
  - `portfolio.position_sizing`:
    - position sizing ロジック（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、銘柄別上限、aggregate cap によるスケールダウン、費用バッファ（cost_buffer）を考慮した安全な調整アルゴリズムを実装。

- ユーティリティ
  - `utils.logging_setup`: ルートロガーの統一設定ユーティリティを追加。
    - stdout ストリームハンドラと日次ローテート（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR 環境変数対応、既存ハンドラのクリア。
    - ファイル出力に失敗した場合はコンソールのみで継続する堅牢設計。
  - `utils.process_priority`:
    - Windows と POSIX を吸収するプロセス優先度設定（set_process_priority）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）。
    - 権限不足や未対応環境に対する警告処理を実装。

- ツール / レポート
  - `tools.paper_verification_report`: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Fill Rate）、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。
    - 各クエリはテーブルが存在しない場合に対して例外を捕捉し安全に N/A を返す。

- 研究モジュール（骨格）
  - `research.factor_research`（ファクター計算モジュールの骨格）を追加。モメンタムや MA200 乖離、ATR、出来高等の指標を DuckDB の `prices_daily` から算出する方針で実装開始（モジュール内に定数と関数の雛形を含む）。

### Changed
- （本初期リリースにつき該当なし）

### Fixed
- .env パースの改善により、引用符付き値のエスケープや行内コメント処理を修正（以前の単純パースでの誤解釈対策）。
- Logging 設定で既存ハンドラの重複登録を防止するため、起動時に既存ハンドラを flush/close して削除するように変更。

### Security
- .env の生成時に注意喚起コメントを追加（.env を Git にコミットしないよう明示）。
- 必須環境変数未設定時の明示的なエラーを用意（Settings._require）。

### Notes / Implementation details
- Paper Trading 用 DB を本番 DB と分離（Settings.paper_sqlite_path）。KABUSYS_ENV=paper_trading 時は専用 DB を使用。
- `PAPER_FILL_MODE` の有効値制約を実装（"instant" / "partial" / "never" / "reject"）。不正値は ValueError。
- kill/stop フラグ周り:
  - 起動時に Kill Flag を自動クリアする振る舞いは `KILL_FLAG_CLEAR_ON_START` で制御（デフォルト 0）。validate_config では本番 env での危険設定に対して警告を出す。
- ログローテーションは日次で 30 日分保持（バックアップ数）。
- `set_process_priority` と `set_cpu_affinity` は権限やプラットフォーム非対応時に安全にスキップする実装（警告ログ）。

---

今後の予定（例）
- research.factor_research の関数実装完了（SQL/計算ロジック）。
- ExecutionEngine / Broker クライアント周りの追加テスト、MockBroker の詳細な挙動定義。
- 単体テスト・CI の整備、config/*.yaml の自動生成・バリデーション強化。
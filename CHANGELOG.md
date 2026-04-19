# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

最新の変更は一番上に記載します。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、ペーパートレード検証レポートなどを収録。

### Added
- 基本情報
  - パッケージバージョンを設定: `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視用停止フラグファイル（data/stop_requested.flag）を検出して安全にループを終了。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 停止フラグ・PID ファイルの取り扱いを実装（data/stop_requested.flag および data/execution.pid）。
    - 実行中はデーモンスレッドでエンジンを動作させ、停止フラグを検知したら安全に停止。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
    - .env パース機能を実装（コメント・引用符・export 形式に対応）。
    - OS 環境変数を保護して `.env.local` の上書きを制御する仕組みを導入。
    - Settings クラスを実装し、各種設定値（J-Quants, kabu API, DB パス, PID/kill flag パス, threshold 等）をプロパティとして提供。
    - `PAPER_FILL_MODE` の妥当性チェック、`KABUSYS_ENV` / `LOG_LEVEL` の検証ロジックを追加。

  - config_setup.py
    - 対話式の .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 入力補助、デフォルト表示、シークレットマスク、保存確認を実装。
    - `.env` 書き出しテンプレートを実装（Git にコミットしない旨のヘッダ付き）。

  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML が利用可能な場合）を実装。
    - `--strict` フラグで警告を失敗扱いにできる。

- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた設定を行う。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）を提供 (`set_process_priority`)。
    - CPU affinity 固定機能 (`set_cpu_affinity`) を追加。
    - 権限不足や未対応環境時に安全に失敗するハンドリングを実装。

- ポートフォリオ構築（純関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 `select_candidates`（スコア降順・同点は signal_rank）を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を実装（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を実装（既存保有を踏まえて特定セクターを新規候補から除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（bull/neutral/bear にマッピング、未知の値はフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック `calc_position_sizes` を実装。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・アグリゲート上限（available_cash）を考慮したスケーリング、端数再配分ロジックを実装。
    - コストバッファ（スリッページ・手数料想定）を加味した計算に対応。

- DuckDB / 分析関連
  - 起動スクリプトやツールで DuckDB 接続を初期化する実装を追加（Settings.duckdb_path を使用）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等の指標を算出するレポートを実装。
    - CLI オプションで期間指定（--from/--to）と DB パス指定（--db）に対応。
    - P95 計算、閾値（稼働率99%、成立率90%、送信率95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - テーブル欠損時に安全に N/A を出力するフォールバックを実装。

- 研究用ファクター計算（着手）
  - research/factor_research.py にモメンタム等のファクター計算の骨子を追加（DuckDB を用いた prices_daily 参照、各種期間定数を定義）。※実装は継続中（ファイル末尾が未完）。

### Changed
- .env 読み込み方針
  - 自動ロード順序を OS 環境変数 > .env.local > .env とし、OS 環境変数を保護する挙動を採用。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- run_monitoring/run_execution の起動フロー
  - 起動時にプロセス優先度を "high" に設定する呼び出しを追加して一貫した運用を想定。

### Fixed
- .env パーサーの堅牢性向上
  - 引用符で囲まれた値内のバックスラッシュエスケープ処理、行末のコメント扱い、`export KEY=val` 形式の対応などを実装し、誤解析を避ける。

- ロギングフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合に標準出力のみで継続することで、ログがまったく出力されなくなる問題を防止。

- ペーパートレードレポートの堅牢化
  - SQLite テーブルが存在しない場合でも例外で終了せず N/A を返すように修正。

### Security
- 機密情報取り扱い
  - config_setup のウィザードでシークレット項目（例: J-Quants トークン、kabu API パスワード）は入力時にマスクして表示。
  - .env テンプレートに「.env を絶対に Git にコミットしないこと」を明記。

---

注記:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や設計意図と差異がある場合があります。必要であれば差分や該当ファイルを指定して、より正確な履歴を作成します。
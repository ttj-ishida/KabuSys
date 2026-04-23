# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

注: ここに記載した変更内容は、提供されたソースコードから推測してまとめたものです。

## [Unreleased]

（現在の開発中の変更点はここに記載してください）

---

## [0.1.0] - 2026-04-23

初回公開リリース。主要な機能追加とユーティリティをまとめて導入しました。

### Added（追加）
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite を使用し、本番 DB と分離する動作を実装。
    - 停止用フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いを追加。
    - 背景スレッドで engine.run_session を実行し、停止フラグを検知して安全に停止するロジックを備える。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を利用する設計。
    - 停止フラグ (data/stop_requested.flag) 検知でループを終了。

- 設定・構成関連
  - config.py: 環境変数と設定を一元管理する Settings クラスを追加。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - `.env` / `.env.local` の読み込み順序と OS 環境変数保護を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化機能あり）。
    - 各種設定プロパティを提供（DuckDB/SQLite パス、PID/kill flag パス、しきい値、KABUSYS_ENV 検証等）。
    - PAPER_FILL_MODE の検証（allowed: "instant","partial","never","reject"）。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）。
    - .env の読み込み・確認・書き込みロジックを提供。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML ファイルの存在/パース検証（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール出力 (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度（nice/Windows priority）設定ユーティリティを追加。
    - psutil を使った優先度設定と CPU affinity 設定関数を提供。
    - 未対応 OS や権限不足時は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分に対応した発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）を超える場合のスケールダウンと端数配分ロジック、cost_buffer を考慮した保守的なコスト見積りを実装。

- データ・解析
  - research/factor_research.py（初期実装/骨組み）:
    - モメンタム、ボラティリティ、流動性、バリュー等のファクター計算方針と定数を導入。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計を採用。
    - （ファイル末尾で関数が途中まで実装されているため、今後の拡張を想定）

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB（デフォルト: data/paper_trading.db）を集計し、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを出力するレポート生成スクリプトを追加。
    - パス/フィルタ指定（--from, --to, --db）に対応。P95 計算ロジックと判定閾値（稼働率 >= 99%、成立率/送信率等）を実装。

- パッケージメタ
  - __init__.py にて __version__="0.1.0" を設定。

### Changed（変更）
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い、クォートなし時のコメント判定を実装し、より堅牢な .env 読み込みを実現。

- ログ出力先の統一
  - 全起動スクリプトから共通の setup_logging を呼び出すことでログの一貫性を確保。

### Fixed（修正）
- run_execution/run_monitoring の DB 初期化において monitoring テーブルの存在保証 (init_monitoring_db) を挿入し、初回起動時のエラーを軽減。

- process_priority.set_process_priority:
  - Windows / POSIX の差分処理と例外ハンドリングを行い、権限不足や未対応 OS でのクラッシュを回避。

### Deprecated（非推奨）
- なし（初回リリースのため該当なし）

### Removed（削除）
- なし

### Security（セキュリティ）
- .env は絶対にリポジトリにコミットしない旨の注記を config_setup に明記（セキュリティ注意喚起）。

---

注記:
- ここに記載した機能や詳細（例: EngineConfig のデフォルト値や RiskManager の既定パラメータ等）は、ソースコード内の定義を基にまとめたものです。実際の挙動やパラメータ調整は設定や外部依存（ブローカークライアント、DB 内容、環境変数）によります。
- research/factor_research.py はファイル末尾が途中で切れているように見えるため、ファクター計算の完全実装は今後の作業が必要です。
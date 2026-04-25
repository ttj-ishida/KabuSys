# CHANGELOG

すべての注目に値する変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

- リリース日付はコミット/リリース時の目安です（ここではコードから推測して記載しています）。
- 重大な変更や破壊的変更は明記します。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-04-25

初期公開リリース（推定）。以下の主要機能・ユーティリティを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視データベースは実行環境に関わらず本番用 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検出により安全にループ終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker（ペーパートレード専用 DB を使用）で本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定、実行中は停止フラグで安全停止。
    - PID ファイルの取り扱い、スレッドデーモンによるエンジン実行。

- 設定管理
  - config.py: 環境変数・設定取得モジュールを追加。
    - プロジェクトルート (.git または pyproject.toml) を基準に .env 自動読み込み（`.env` → `.env.local` の優先順）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - .env のパースは引用符、エスケープ、インラインコメント、`export KEY=val` 形式に対応。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading の振る舞いなど）とバリデーションを提供。
    - `paper_fill_mode` の有効値検証（instant/partial/never/reject）。
    - 環境判定 (development/paper_trading/live) やログレベル検証など。

- 設定支援・検証ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - シークレット項目は表示マスク、既存 .env の読み込みとデフォルト値のサポート。
    - 最終確認後に `.env` を書き出し、保存メッセージを表示。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）YAML パースによる検証。
    - `--strict` オプションで警告も失敗として扱う。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。
    - 既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）に対応。
    - ログレベル・ログディレクトリ解決の優先順位を提供。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収（psutil ベース）。
    - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補抽出（タイブレークに signal_rank を使用）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等金額へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの保有比率上限チェックで新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース・等配分・スコア配分に基づく発注株数決定ロジック（単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）。

- 分析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し、閾値と比較して PASS/FAIL を判定。
    - 日付フィルタ、DB パス指定（環境変数または --db）対応。
    - P95 計算ユーティリティ、N/A 表示ロジックを含む。

- 研究用ファクター計算（基盤）
  - research/factor_research.py:
    - モメンタム・ボラティリティ等のファクター計算用モジュールの骨格を追加（DuckDB 接続を受け取る設計）。
    - 定数・計算方針（1M/3M/6M リターン、MA200、ATR、出来高指標など）を定義。

### Changed
- （初期リリースのため無し：既存コードの振る舞いは仕様として導入）

### Fixed
- MONITOR_POLL_INTERVAL のパースで無効値や 0/負値を検出した場合にデフォルトへフォールバックする処理を実装（Time.sleep に渡す不正値対策として警告を出す）。

### Security
- .env は Git に含めない旨の注記を config_setup の生成ヘッダに明記。
- シークレット系設定は対話 UI 上でマスク表示。

### Notes / Implementation details
- DB 初期化: run_monitoring / run_execution 起動時に監視テーブルの初期化（init_monitoring_db）を行い、監視テーブルの存在を保証（冪等）。
- Paper Trading 分離: ペーパートレード時は別 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
- ログ出力: StreamHandler は stdout を使う（cron 等のリダイレクト運用を想定）。
- process_priority, cpu_affinity: 実行環境の権限や OS によっては設定できない場合があるため、失敗時には警告を出して継続する実装。

---

上記はコードの内容から推測して作成した CHANGELOG です。各項目の文言や日付は実際のリリース履歴に合わせて調整してください。必要であれば、各ファイルごとのより詳細な変更点（関数型シグネチャや設定キーの一覧など）も追記できます。
# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20
初回リリース。以下の主要機能・実装を含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離してペーパートレード運用が可能。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する旨の挙動を実装。
    - 停止フラグの検知によるループ終了と KeyboardInterrupt のハンドリング。

- 設定管理・セットアップ・検証
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と OS 環境変数保護（上書き禁止）を実装。
    - 複雑な .env のパース実装（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱い）。
    - Settings クラスを実装（J-Quants、kabu API、DB パス、paper_trading 用パス、監視閾値、環境判定ユーティリティ等のプロパティ）。
    - PAPER_FILL_MODE の検証（有効値の限定）など設定値検証を実装。
  - config_setup.py
    - .env を対話形式で作成／更新するウィザードを実装。既存値の読み込み、シークレットのマスク表示、保存確認を含む。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の有無と（PyYAML 時）パース検証、および本番環境向け追加ガードチェックを実装。
    - --strict オプションにより警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 世代保持）を設定するユーティリティを実装。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順序を明確化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - psutil を用いてプラットフォーム差分を吸収したプロセス優先度設定関数 set_process_priority(level) を実装（Windows / POSIX をサポート）。
    - set_cpu_affinity による CPU ピンニングユーティリティを実装（利用不可・権限不足時は警告してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates: score 降順、同点時 signal_rank）を実装。
    - 重み計算: calc_equal_weights（等分配）、calc_score_weights（スコアに応じた正規化、全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を超える場合に候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数決定ロジックを実装。
    - 単位株（lot_size）丸め、per-position および aggregate キャップ、cost_buffer による保守的見積り、スケーリングと残差配分ロジックを実装。

- 実行／モニタリング DB 初期化と DuckDB 統合
  - monitoring_db の初期化呼び出し（init_monitoring_db）を各起動スクリプトで行うことで監視用テーブルの存在を保証。
  - DuckDB 接続を各種モジュール（実行エンジン、リサーチ）で使用する実装を追加。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95））を集計し、PASS/FAIL 判定を行うレポート生成ツールを実装。
    - P95 計算、期間フィルタ (--from/--to)、閾値による判定ロジックを実装。

- 研究用モジュール（初期実装）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールの骨組みを実装（DuckDB 接続を受け取る設計、モメンタム期間定数など）。モメンタム計算の実装が進行中（ファイル末尾が実装途中の状態）。

### Changed
- なし（初回リリースのため変更履歴はなし）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

補足メモ（実装上の注意点・既知の制約）
- .env の自動読み込みはプロジェクトルートが見つからない場合はスキップされます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- process_priority / CPU affinity 操作は権限の問題やプラットフォーム依存で失敗することがあり、その場合は警告ログを出してスキップします。
- portfolio.position_sizing.calc_position_sizes の価格欠損（価格が 0）の扱いについては TODO コメントがあり、将来的にフォールバック価格の導入を検討中です。
- research/factor_research.py はファクター計算ロジックの実装が一部未完了です。リサーチ機能の完全利用には追加実装が必要です。

---

開発者向け: 本 CHANGELOG はソースコードの現状から推測して作成しています。必要に応じて各項目を編集・補完してください。
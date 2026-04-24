# Changelog

すべての変更は Keep a Changelog 規約に従って記載しています。  
重要な変更点のみを記載しています。

## [0.1.0] - 2026-04-24

### Added
- 全体
  - 初期リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築・ポジション算出ロジック、設定ツール、検証ツール等を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きを実装（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
    - 停止制御としてプロジェクト直下の `data/stop_requested.flag` を参照し、フラグを検知するとループを停止。
    - 監視は実行環境に関わらず本番用の SQLite パス（Settings.sqlite_path）を利用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading SQLite を使用して本番 DB と完全に分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組立て、ExecutionEngine の起動・停止制御を実装。
    - 停止フラグ `data/stop_requested.flag` の検知でエンジン停止または起動を中止。
    - 実行プロセスの PID を `data/execution.pid` に記録する仕組みを想定（pid_file の利用）。

- 設定管理
  - config.py
    - .env の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml から検出）。優先順位は OS 環境 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト等向け）。
    - .env 解析機能を強化：`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱い、コメント除去ルールに対応。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API、DB パス、paper trading 関連、監視閾値、ログレベルなど）をプロパティ経由で取得・検証。
    - PAPER_FILL_MODE（paper trading の fill 動作）に対するバリデーション（有効値: instant|partial|never|reject）。
    - 各種閾値・フラグ（CPU/MEM/DISK の閾値、KILL_FLAG 関連）を環境変数から取得するプロパティを用意。

  - config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。
    - シークレット項目（トークン等）はマスク表示し対話入力をサポート。
    - デフォルト値や選択肢を提示、保存前の確認、保存処理（.env の整形）を実装。
    - .env の書き込みは Git へ絶対にコミットしない旨の注意文を含むテンプレートで出力。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config YAML の存在・パースチェック（PyYAML が未インストールの場合は警告としてスキップ）等を実装。
    - `--strict` フラグで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログディレクトリ解決ロジック（引数 > 環境変数 LOG_DIR > デフォルト logs/）と、作成失敗時のフォールバック（ファイル出力を無効化してコンソールのみ）を実装。
    - ログレベル解決（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティを追加（psutil 利用）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境では警告を出して安全にスキップする。

- ポートフォリオ構築・リスク制御
  - portfolio/portfolio_builder.py
    - シグナルの上位選定（score ソート）、等金額配分、スコア加重配分を提供（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター別集中上限の適用（既存保有額からセクターエクスポージャを算出して候補を除外）と、マーケットレジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py
    - weight / candidates / portfolio_value 等をもとに発注株数を算出するロジックを実装。
    - allocation_method による分岐（risk_based / equal / score）。lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング、残余キャッシュによる端数配分ロジックを搭載。

- 監査・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - DB テーブルが存在しない場合に耐性を持つ実装（OperationalError を捕捉して N/A で出力）。

- 解析・研究
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受けてモメンタム / ボラティリティ / バリュー等のファクターを計算する設計を追加（モジュール骨子と定数、calc_momentum のコメント・仕様を追加）。実装の続きが存在することを示唆。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Notes / Implementation details
- run_monitoring は Monitoring 用 DB 接続に通常の Settings.sqlite_path（本番 DB）を使用する仕様になっており、環境に依らず監視データは本番 DB に記録される点に注意。
- run_execution は paper_trading 環境時に専用 SQLite（Settings.paper_sqlite_path）を使用し、本番データと分離するため安全にペーパートレードを実行可能。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後やインストール環境での挙動に影響する場合がある。
- ログディレクトリ作成に失敗するとコンソール出力のみで稼働し、起動エラーとならないよう設計されている。
- process_priority と CPU affinity の設定は権限や OS により失敗する可能性があるため、失敗時は警告を出して処理を継続する。

---

今後の改善候補（メモ）
- research/factor_research.py の未完実装部分の完成。
- 銘柄別 lot_size の拡張や価格フォールバックロジック（risk_adjustment の TODO）。
- より詳細なログ・メトリクス収集、Monitoring の監視指標強化。
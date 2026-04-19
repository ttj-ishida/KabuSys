CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

フォーマット:
- 変更は各リリースごとに分類されています（Added, Changed, Fixed, ...）。
- 日付はリリース日を示します。

[Unreleased]
------------

- 今のところ未リリースの変更はありません。

0.1.0 - 2026-04-19
------------------

Added
- 初回公開リリースを追加。
- コア実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用し、本番 DB と分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を監視し、検出時にエンジンを安全に停止。
    - 実行中の PID を data/execution.pid に書き込む想定（pid_file 引数を受け渡し）。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による終了対応。
    - SQLite / DuckDB の接続管理と初期化呼び出し（init_monitoring_db）を実装。

- 設定管理
  - config.py: 環境変数 / .env ファイルの自動読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動ロードを行う。
    - .env のパース機能を強化（export プレフィックス対応、クォート値のバックスラッシュエスケープ考慮、インラインコメント処理）。
    - .env 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings で各種設定プロパティを提供（J-Quants / kabuAPI / DB パス / PAPER_FILL_MODE / PID・Kill flag・しきい値等）。
    - 入力検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェック）。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 標準項目の定義、既存 .env 読み込み、シークレットのマスキング、保存確認を実装。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数存在チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML が無ければスキップ）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番（live）向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性の警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み計算（等配分・スコア加重）を実装。
    - スコア降順ソート、signal_rank によるタイブレークを実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバック。
  - portfolio/position_sizing.py: 株数算出ロジックを実装。
    - risk_based / equal / score の allocation_method に対応。
    - lot_size（単元株）丸め、per-stock 上限・aggregate cap（利用可能現金に合わせてスケールダウン）を実装。
    - cost_buffer を考慮した保守的コスト見積・スケールダウンロジック、余裕資金での端数（lot 単位）配分アルゴリズムを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - 既存保有からセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外するロジック。
    - market_regime に応じた乗数（bull/neutral/bear）を返却。未知レジームは警告して 1.0 にフォールバック。

- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを実装。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / app_name によるログファイル保存、既存ハンドラのクリア、30 日間のローテーション保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: psutil を利用したプロセス優先度 / CPU affinity 設定を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して set_process_priority を提供。
    - set_cpu_affinity で先頭 N コアへの固定（利用可能コア数のチェック、アクセス権エラーは警告でスキップ）。

- データベース / 分析
  - duckdb の接続を受け取る設計を採用（Execution / Monitoring で duckdb_path を使用）。
  - monitoring の初期化（init_monitoring_db）呼び出しを起動スクリプトで行い、監視用テーブルの存在を保証。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/p95）等を集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（例: uptime >= 99%, fill_rate >= 90% 等）を定義。
    - --from / --to / --db オプションをサポート。
    - latency の P95 算出ロジックを実装。

- 研究モジュール（factor_research）
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、出来高系などを想定）。
    - DuckDB 経由で prices_daily / raw_financials を参照してファクターを計算する設計。モジュール内に定数と calc_momentum の実装骨子を用意。

Changed
- プロジェクト構成
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

Notes / 備考
- 設定や挙動は多くが環境変数で制御されます。代表的な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, PAPER_FILL_MODE
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB, デフォルト: data/paper_trading.db)
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH 等
- .env の自動ロードはプロジェクトルートを検出できた場合に実行されます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring と run_execution は stop フラグファイル（data/stop_requested.flag）および kill/pid ファイルを用いる運用を想定しています。
- 一部モジュール（研究モジュール等）は将来的な拡張を見越した TODO コメントや不完全なパーシャル実装を含みます。

今後の予定（例）
- テストカバレッジの追加（ユニットテスト、特に金額計算・スケールダウンロジック）
- 銘柄ごとの lot_size 対応、価格フォールバックロジック（price が欠損した場合の補完）
- DuckDB を用いたファクター計算の最適化・追加ファクター実装
- 実行エンジンの永続化/監視の強化（プロセスマネージャ統合、Prometheus/メトリクス出力等）

--- 

注: 上記の変更履歴は提示されたソースコードから推測して作成したものであり、実際のコミット履歴・リリースノートとは差異があり得ます。必要であれば、より詳細にソースファイルごとの変更点や想定ユースケースを反映した修正版を作成します。
# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
慣習により日付はコード解析日（このファイル作成日）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーション構成を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
- 実行/監視用エントリポイントを追加
  - `run_execution.py`
    - ExecutionEngine の起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV により paper_trading 時は専用 SQLite (data/paper_trading.db) を使用し、本番 DB と分離。
    - Broker クライアントを `BrokerClientFactory` 経由で生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine.run_session` をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知時に安全に停止する機能。
    - PID ファイル (`data/execution.pid`) を利用。
    - RiskConfig にデフォルト値を導入（例: max_position_pct=0.20, max_utilization=0.80 等）。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト。
    - デフォルトポーリング間隔 60 秒（環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。無効値はデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を利用（monitoring 用テーブルを初期化）。
    - 停止フラグでループ終了、KeyboardInterrupt に対する安全なクローズ処理。
- 設定・環境変数管理
  - `config.py`
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
    - `.env` と `.env.local` の読み込み優先度:
      - OS 環境変数 > .env.local > .env
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 高度な .env パーサ実装（export 形式、クォートとエスケープ、行内コメント処理など対応）。
    - 必須環境変数取得ヘルパ `_require()`（未設定時に明示的なエラー）。
    - 多数の設定プロパティを提供（DB パス、paper_trading 用設定、監視閾値、ログレベル、環境判定等）。
    - `paper_fill_mode` に妥当性チェック（instant/partial/never/reject）。
- 設定支援・検証 CLI
  - `config_setup.py`
    - 対話式ウィザードで `.env` を生成／更新。
    - 秘匿項目はマスク表示。既存値の再利用やデフォルト値の採用が可能。
    - `.env` の書式化出力を実装（コメント付きテンプレート）。
  - `validate_config.py`
    - 起動前に .env と config/*.yaml を検証する CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML が存在する場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境向けの安全ガード（LINE 設定や Kill Switch の注意喚起）。
- ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler (日次ローテーション、30日保持) を設定する共通ユーティリティ。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。ログレベルの解決順を明示。
    - stdout を使う設計（cron 等でのリダイレクトを考慮）。
  - `utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定（スコア降順 + tie-break に signal_rank）`select_candidates`
    - 等分配重み `calc_equal_weights`
    - スコア正規化重み `calc_score_weights`（全スコアが 0 の場合は等分配へフォールバック）
  - `portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター別エクスポージャ評価による候補除外）
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear による乗数、未知値は警告のうえ 1.0 にフォールバック）
  - `portfolio/position_sizing.py`
    - 発注株数計算 `calc_position_sizes`
      - 複数の allocation_method をサポート: `risk_based`, `equal`, `score`
      - lot_size（単元）に合わせた丸め、1 銘柄上限・aggregate cap（available_cash）でのスケールダウン、
      - cost_buffer による保守的なコスト見積り、端数処理のための残差順配分を実装
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能）を参照し、検証レポートを生成。
    - 集計指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - PASS/FAIL の閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ（--from / --to）、P95 計算、データ欠損時の N/A 表示を実装。
- research/factor_research（ファクター計算モジュール）を追加（Momentum, Value, Volatility, Liquidity を想定する設計）
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算する設計。
  - 実装の一部にモメンタム計算 `calc_momentum` が含まれる（ファイル末尾にて実装が途中で切れている箇所あり）。

Changed
- ロギングの標準化
  - 全起動スクリプトから `utils.logging_setup.setup_logging` を呼び出す設計でログ出力を統一。
  - ファイルローテーションと stdout 出力の組合せにより運用ログの取り扱いを簡素化。
- 環境変数ロードの方針を明確化
  - 自動ロードの際に OS 環境変数を保護（protected set）して `.env.local` からの上書きを制御。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化を追加。

Fixed
- DB 初期化の冪等化
  - `init_monitoring_db` を実行して監視テーブルの存在を保証（既存 DB に対しても安全に何度でも呼べる）。

Notes / Known limitations
- research/factor_research モジュール内の一部関数が途中で切れている（calc_momentum の末尾が未完）。今後の実装継続が必要。
- `process_priority` や `set_cpu_affinity` は権限や OS に依存するため、実行環境によっては設定を行えないケースがある（警告でスキップ）。
- `apply_sector_cap` は価格データ欠損時のフォールバックに関する TODO を含む（価格が 0.0 の場合にエクスポージャーが過少見積になる可能性あり）。
- Paper Trading と本番 DB の分離は設計上保証されているが、環境変数の設定ミスによる混在リスクに注意（`validate_config` の活用を推奨）。

Security
- シークレット値（J-Quants トークンや kabu API パスワード）は `.env` に保存する設計だが、`config_setup` では .env を Git にコミットしないよう強調している。運用時は機密管理の方針に従ってください。

---

（今後）
- research モジュールの完成、strategy/engine 周りの追加ユニットテスト、YAML ベースの設定検証強化、各種エラーハンドリングとメトリクス強化を予定しています。
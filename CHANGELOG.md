Keep a Changelog に準拠した変更履歴を以下に日本語で作成しました。
コード内容から推測してまとめています。必要に応じて日付や細部を調整してください。

CHANGELOG.md
=============

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に従っています。

## [Unreleased]

### 追加 (Added)
- 環境設定ウィザードを追加（kabusys.config_setup）
  - 対話式で .env を生成・更新する CLI（python -m kabusys.config_setup）。
  - 複数項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL 等）をサポート。
- 設定検証ツールを追加（kabusys.validate_config）
  - .env と config/*.yaml の存在・基本妥当性チェックを行う CLI（--strict オプションあり）。
- Settings クラスによる環境変数管理を追加（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートが特定できる場合）。
  - 必須環境変数取得ヘルパ、Paper Trading 用設定、閾値系設定、環境種別判定を提供。
- 実行系の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。Paper Trading 時は専用 DB を使用し MockBroker を利用する想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を設定可能。
- Paper Trading 用検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - 日付フィルタ、稼働率 / 注文成功率 / レイテンシ（平均・P95）等を集計してレポート出力。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - 候補選定、等金額・スコア加重重み計算（portfolio_builder）。
  - セクター集中制限、レジーム乗数（risk_adjustment）。
  - 発注株数算出・リスク制御・単元丸め（position_sizing）。
- ユーティリティを追加（kabusys.utils）
  - logging_setup: stdout + 日次ローテートファイルハンドラで統一ログ設定。
  - process_priority: Windows/Linux/macOS を吸収するプロセス優先度と CPU affinity 設定ユーティリティ。
- DuckDB と SQLite を併用する設計を導入
  - 分析用に DuckDB（kabusys.duckdb）、監視/履歴用に SQLite を利用する実装例を含む。
- 研究モジュール（kabusys.research.factor_research）にモメンタム算出の実装開始（未完の箇所あり、今後拡張予定）。

### 変更 (Changed)
- .env 読み込みロジックを強化（kabusys.config）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを実装。
  - OS 環境変数は protected として .env の上書きを制御。
- ログ出力のデフォルトを stdout に統一（logging_setup）
  - StreamHandler を stdout に設定し、cron/Task Scheduler 等でのリダイレクト運用を想定。
  - ファイルハンドラは日次ローテーション（30 日保持）で追加。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続。
- run_monitoring の挙動
  - 監視用プロセスは環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用して監視データを保管する設計に変更（運用方針）。
  - 停止フラグ（data/stop_requested.flag）の検知でループ終了する安全機構を追加。
- run_execution の挙動
  - paper_trading 環境時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定する挙動を追加。
  - ExecutionEngine の起動時に PID ファイル管理、停止フラグ検知によるシャットダウン処理を追加。
- calc_score_weights のフォールバック
  - 全銘柄スコアが 0.0 の場合は等金額配分にフォールバックし WARN を出力するように変更。
- position_sizing のアロケーション・スケーリング
  - aggregate cap（総投下資金）が available_cash を超える場合のスケーリングと残余の lot 単位での再配分ロジックを実装（端数処理と安定性改善）。
- apply_sector_cap の挙動
  - sector_map に存在しない銘柄は "unknown" 扱いとしてセクター上限判定の対象外とする（誤検出抑止）。
- process_priority の堅牢化
  - 未対応 OS やパーミッションで失敗した場合に警告を出してスキップするように変更。

### 修正 (Fixed)
- .env パーサーの不備を修正（空行・コメント・export・クォート時のエスケープ処理など）。
- logging_setup: ログディレクトリ作成失敗時にハンドラ設定で例外が上がる問題を回避（ファイルハンドラをスキップして続行）。
- run_monitoring/run_execution: DB コネクションを finally ブロックで確実にクローズするように修正。
- paper_verification_report: データ欠如やテーブル未存在時に操作が失敗するのを防ぐため、sqlite3.OperationalError を捕捉してデフォルト値で処理する耐障害性を追加。
- set_process_priority / set_cpu_affinity: アクセス権限や未実装例外をキャッチしてログに警告を出すよう修正。

### ドキュメント (Documentation)
- 各スクリプト・モジュールに使用法や設計方針の docstring を追加／強化。
- config_setup、validate_config、paper_verification_report に CLI ヘルプと使い方を明示。

### 既知の問題 / TODO
- position_sizing: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり（TODO コメントあり）。将来的に前日終値等のフォールバック導入を検討。
- research.factor_research のモメンタム関数実装が途中でファイル末尾が切れている（未完）。追加のファクター計算関数（Value/Volatility/Liquidity）の実装が必要。
- 一部の機能（ExecutionEngine、BrokerClient など）は外部モジュールとの結合を前提としており、実働確認には依存モジュールと設定が必要。

---

## [0.1.0] - 2026-04-22

初回公開リリース（ベース実装）。主な内容は以下。

### 追加 (Added)
- 基礎アーキテクチャと主要モジュールを実装
  - 環境設定・読み込み機構（kabusys.config）
  - 実行・監視用エントリポイント（run_execution.py, run_monitoring.py）
  - ExecutionEngine 周辺の骨格（OrderRepository / OrderManager / RiskManager / Reconciler の利用例）
  - 監視 DB 初期化ユーティリティ（monitoring_db の初期化呼び出し箇所）
  - ロギング設定ユーティリティ（ログの統一設定）
  - プロセス優先度 / CPU affinity ユーティリティ
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、リスク調整）
  - Paper Trading 用検証レポートツール
  - config_setup（.env ウィザード）と設定検証ツール（validate_config）
  - DuckDB と SQLite を併用するデータ基盤設計の雛形
- パッケージバージョンを 0.1.0 に設定（kabusys.__version__）

### 変更 (Changed)
- 初期実装のためのデフォルト設定と CLI を整備（詳細は各モジュールの docstring を参照）。

### 既知の問題
- 研究用モジュールの一部はまだ実装途中（将来的に拡張予定）。

---

注意事項 / 移行ガイド
- 本パッケージを運用に入れる前に以下環境変数が必須（validate_config で検出可能）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 本番運用時の推奨設定:
  - KABUSYS_ENV=live の場合は .env の内容を慎重に確認する（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等）。
  - KILL_FLAG_CLEAR_ON_START は本番では 0（自動クリアしない）を推奨。
- 新規 / 変更された主要環境変数:
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite DB
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
  - LOG_DIR / LOG_LEVEL: ログディレクトリ、ログレベルの指定
- データベースの分離:
  - paper_trading 環境では実行エンジンは paper_trading 用 DB を使用し、本番 monitoring DB と分離されます。監視ツールは環境に関わらず監視 DB（デフォルト data/monitoring.db）を使用します（運用方針に基づく設計）。

もし CHANGELOG の粒度や日付、あるいは「どの変更をどのリリースに含めるか」を具体的に指定いただければ、それに合わせて調整した版を作成します。
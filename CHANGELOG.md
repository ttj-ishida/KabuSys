# Changelog

すべての重要な変更点をこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

全般ルール:
- バージョンは semantic versioning を想定します。
- 日付はリリース日です。

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-25
初回リリース。以下の主要機能・ユーティリティを含みます。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は実行環境にかかわらず本番用の SQLite パスを使用する仕様。  
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全に終了。  
    - duckdb と sqlite 接続を行い monitoring DB の初期化を実行。
  - run_execution: ExecutionEngine 起動スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` 時は専用の paper_trading DB を使用（本番 DB と分離）。  
    - BrokerClientFactory を利用したブローカークライアントの作成、OrderManager / RiskManager / Reconciler 等の組み立て、ExecutionEngine の起動を行う。  
    - 停止フラグ/実行 PID ファイルの管理を実装。スレッドベースで実行し、停止フラグでエンジンを停止可能。

- 設定管理（config）
  - Settings クラスで環境変数から各種設定値を抽象化（DB パス、API トークン、Paper Trading 設定、閾値など）。  
  - .env 自動ロード機能を導入（プロジェクトルートを .git / pyproject.toml から自動検出）。  
  - PAPER_FILL_MODE（ペーパートレードの約定モード）等の厳密なバリデーションを実装。  
  - is_live / is_paper / is_dev の便宜プロパティ。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新するツールを追加。  
    - 必要項目のプロンプト、シークレット入力の扱い、確認後の .env 保存をサポート。
  - validate_config: 起動前チェックツールを追加。  
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在＆パース（PyYAML がある場合）など。  
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング & 実行ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加。  
    - StreamHandler を stdout に出力、TimedRotatingFileHandler を日次ローテーション（30日保持）で設定。  
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: プロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。  
    - Windows / POSIX の差分を吸収し、psutil を用いて安全に実行。アクセス権不足等は警告でスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
    - スコア降順・タイブレーク実装、スコア全0 の場合は等金額配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。  
    - 既存保有のセクター別エクスポージャ計算、上限超過セクターの除外、レジームに応じた乗数（bull/neutral/bear）を実装。  
  - portfolio.position_sizing: 発注株数決定ロジック（calc_position_sizes）。  
    - risk_based / equal / score の配分方式を実装。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウンと残差の配分）、cost_buffer を加味した保守的見積り。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計。  
    - 閾値に基づく PASS/FAIL 判定（稼働率 99%、注文成功率 90% 等）。  
    - --from/--to/--db オプション対応、PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。

- 研究用モジュール（スケルトン）
  - research.factor_research: DuckDB を使ったファクター計算のモジュールを追加（モメンタムや MA200、ATR、流動性等の計算を想定した設計）。  
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照する設計方針（まだ一部実装途中あり）。

- パッケージ構成
  - tools, portfolio, utils, monitoring, execution 等の名前空間エクスポートを含む。

### Changed
- ロギングの挙動（設計）: ログを stderr ではなく stdout に出力する方針を採用（cron / Task Scheduler での扱いを考慮）。
- .env 読み込みの優先度: OS 環境変数 > .env.local > .env の順でロード。`.env.local` は上書き可能。

### Fixed / Robustness
- .env パーサを強化
  - export KEY= 候補に対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱いを改善。
  - 無効行や空行、コメント行を適切に無視するようにした。
- DB 初期化の冪等性
  - run_execution, run_monitoring 起動時に監視テーブルの初期化（init_monitoring_db）を呼び出し、既存 DB があっても安全に実行。
- process_priority / set_cpu_affinity: アクセス権限や未対応プラットフォームで失敗した場合に警告を出してスキップする安全策を追加。
- Paper レポート: P95 の算出や latency_ms NULL の扱いを明示的に処理。

### Security
- シークレット項目（J-Quants トークン、KABU API パスワード等）は config_setup の表示でマスクするように実装し、.env を Git にコミットしない旨の注意書きをテンプレートに追加。

### Notes / Known issues
- research.factor_research モジュールの一部実装が未完（ソースの末尾が未完了の箇所あり）。今後のリリースで完成予定。
- position_sizing の price 欠損時のフォールバックは現状未実装（TODO コメントあり）。価格欠損があるとエクスポージャが過少見積りされる可能性あり。
- 一部機能は外部依存（psutil, duckdb, PyYAML 等）に依存しており、利用環境により動作が制限される場合がある。

---

注: 上記はコードベースの内容から推測してまとめた CHANGELOG です。実際のリリースノートとして公開する際は、テスト結果や意図したリリース日付・責任者・互換情報などを追加してください。
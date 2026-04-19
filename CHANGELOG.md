# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19
初回リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution: ExecutionEngine を起動するメインスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用 DB（環境変数で指定可能、デフォルト data/paper_trading.db）に完全分離して記録する。
    - 停止判定用フラグファイル（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
    - エンジンを別スレッドで起動し、停止フラグ検知で安全に停止するループを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。

- 環境設定関連
  - Settings クラス（kabusys.config）を追加。環境変数から各種設定を取得するヘルパを提供。
    - DB パス、PID/kill フラグパス、しきい値などをプロパティとして取得。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）を実装。
    - settings インスタンスをデフォルトでエクスポート。
  - 自動 .env 読み込み機能を導入（プロジェクトルートに基づく .env / .env.local 読み込み）。  
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env 設定ウィザード CLI（kabusys.config_setup）を追加。対話式で .env を作成/更新できる。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数や YAML 設定ファイル等の事前チェックを行う。`--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく解決順を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続するフェールセーフ。
  - プロセス優先度／CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。psutil を用いて Windows / POSIX を吸収する簡易 API（set_process_priority, set_cpu_affinity）を提供。権限不足等の失敗は警告でスキップ。

- モニタリングDB初期化
  - monitoring のための DB 初期化ヘルパ（init_monitoring_db）呼び出しを起動フローに組み込み（冪等）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。  
    - calc_score_weights は全スコアが 0.0 の場合に等金額配分へフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を追加。  
    - apply_sector_cap は sell_candidates（当日売却予定）をエクスポージャー計算から除外。'unknown' セクターは上限適用対象外。
    - calc_regime_multiplier は "bull", "neutral", "bear" をマップし、未知のレジームは 1.0 でフォールバック（警告）。
  - position_sizing: 発注株数計算 (calc_position_sizes) を追加。  
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size に基づく丸め、ポジション上限（max_position_pct）や投下上限（max_utilization）、aggregate cap によるスケールダウンを実装。
    - cost_buffer を用いた保守的なコスト見積り、残差処理で lot_size 単位の再配分を行うロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite データから稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL レポートを出力する CLI を追加。しきい値（稼働率99%、成功率90%、送信率95%、P95レイテンシ200ms）を定義。

- リサーチ基盤
  - research/factor_research の骨組みを追加（モメンタム等ファクター計算の方針と一部定数を実装）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。calc_momentum の実装開始（ファイル末尾で未完の箇所あり）。

### 変更 (Changed)
- .env 読み込みの挙動を明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護され、.env.local は上書き可能。
- ログ設定の解決順を定義
  - ログレベルは (1) 引数、(2) 環境変数 LOG_LEVEL、(3) デフォルト "INFO" の順で決定。
  - ログディレクトリは (1) 引数、(2) 環境変数 LOG_DIR、(3) デフォルト "logs/" の順で決定。
- プロセス優先度設定は起動直後に行うように統一（実行 / 監視スクリプト両方で set_process_priority("high") を呼び出し）。

### 修正 (Fixed)
- .env パーサーの強化
  - export プレフィックスのサポート、クォート文字内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート外での '#' を条件付きでコメントとして扱う）などを実装し、より柔軟に .env をパース可能にした。
- ロギング初期化の安全性
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソールログのみで継続動作するようにし、起動失敗を回避。

### 既知の制限 / 注意点 (Known issues / Notes)
- run_monitoring は「監視用 DB として常に本番 sqlite_path を使用する」設計になっており、KABUSYS_ENV に依存せず本番用の SQLite パスを参照します。テスト環境で監視データを分離したい場合は sqlite_path の環境変数を適切に設定してください。
- research/factor_research の calc_momentum はファイル末尾で未完（実装途中）の箇所があります。ファクター計算機能を利用する際は該当関数の完成度に注意してください。
- 一部機能（例: BrokerClientFactory、ExecutionEngine、SystemMonitor、監視DBスキーマ定義など）は本 changelog の範囲での実装呼び出し点を含みますが、詳細な内部実装は別モジュールに分かれています。運用前に validate_config や config_setup を利用して環境を整えてください。

### セキュリティ (Security)
- 特記事項なし。

---

今後のリリースでは、research モジュールの完成、ExecutionEngine / Broker クライアントのテストカバレッジ強化、さらに細かなログ・メトリクスの出力拡張などを予定しています。
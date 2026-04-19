# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。日付は本リリース作成日です。

## [Unreleased]

## [0.1.0] - 2026-04-19

### 追加
- 全体
  - 初期リリース。パッケージ名: KabuSys（日本株自動売買システム）。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト / デーモン
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - プロセス優先度を高 (`high`) に設定してから起動。
    - エンジンは別スレッドで実行され、data/stop_requested.flag による外部停止をサポート。
    - 実行中の PID を data/execution.pid に記録する仕組み（pid_file パスの受け渡し）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 監視は環境にかかわらず production 用の sqlite_path（デフォルト: data/monitoring.db）を使用する設計。

- 設定 / 設定補助
  - config.py: 環境変数と設定管理を提供。
    - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を探索して検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプションを追加。
    - 必須環境変数取得ヘルパ `_require()`、各種設定値（DB パス、PAPER_FILL_MODE、閾値、PID/kill flag パスなど）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 推奨初期値、シークレット入力、選択肢サポート、.env 上書き保存機能を提供。
    - 保存時に注意喚起（.env をコミットしない等）。

- 設定検証
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML 未インストール時は警告してスキップ）、本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
    - --strict オプションで警告を FAIL と扱う。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリア機能、LOG_LEVEL / LOG_DIR の解決ロジックを実装。ファイル出力作成失敗時は Console のみで継続。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。
    - Windows / POSIX を吸収した優先度設定（high/normal/low）と CPU affinity 設定機能を提供。
    - 権限や未対応 OS に対する安全な失敗処理（警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分を実装（全スコアが 0 の場合は等分配にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑えるため既存保有のセクター比率に基づいて新規候補を除外するロジックを追加（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは WARNING と共に 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数決定を実装。
      - リスクベース計算（risk_pct, stop_loss_pct）と 1 銘柄上限、lot_size（単元）丸め、available_cash による aggregate cap、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリング、残差に基づく追加配分ロジックを実装。
      - 不足データ（価格欠損）時にはスキップして安全な動作を保証。

- モニタリング / DB 初期化
  - monitoring_db 初期化呼び出しを run_execution.py/run_monitoring.py で行い、監視用テーブルの存在を冪等的に保証。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成スクリプトを追加。期間指定（--from/--to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - 指標:
      - 稼働率（system_status から uptime_pct）、総ポーリング数、エラー数
      - 注文関連: Created / Filled / Sent 件数、注文成功率（Filled/Created）、送信率（Sent/Created）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg, max, P95）— P95 は全値から計算（latency_ms が NULL の行は除外）
    - 合否基準（閾値）を定義して PASS/FAIL を出力（稼働率、成功率、送信率、P95 レイテンシ等）。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、ボラティリティ、バリュー、流動性を想定）。DuckDB 経由で prices_daily/raw_financials を参照し、(date, code) をキーとする結果を返す設計。モジュールは設計方針と定数を含む。  

### 変更
- 設定の自動ロード
  - .env/.env.local の自動ロード実装により、CWD に依存しないプロジェクトルート検出方式を導入（.git または pyproject.toml を基準に探索）。
- ログ出力
  - 日次ログローテーションと stdout を使う方針を統一。既存ハンドラの二重登録を防止するため、セットアップ時にハンドラをクリアするよう変更。

### 修正
- 環境変数パースの堅牢化
  - config._parse_env_line において、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理を考慮することで .env の多様な書式に対応。
- run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL の不正な値に対して警告を出しデフォルト（60 秒）へフォールバックする挙動を追加。
- process_priority: プラットフォーム差分（Windows の定数、POSIX の nice、未対応 OS）の扱いを整備し、権限不足時に警告して続行するよう変更。

### 既知の問題 / 注意点
- research/factor_research.py は設計と一部実装を含むが、モジュール内部の実装が未完（モメンタム計算の関数の一部が途中）であり、リリース時点では完全実装ではありません。利用時はテストとコード確認を推奨します。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」仕様のため、開発環境でモニタリングを実行する際は監視 DB の指定に注意してください。
- PAPER_FILL_MODE の値チェックが厳密に行われるため、環境変数設定ミスにより起動時に例外が発生する可能性があります（有効値: instant/partial/never/reject）。
- ログディレクトリ作成失敗時はファイル出力が無効になり stdout のみでの出力となります（警告が出ます）。

### セキュリティ
- .env ファイルは生成時に「絶対に Git にコミットしないこと」をドキュメントに明記。シークレット項目はウィザード・表示時にマスクされます。

---

今後の予定:
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の SQL/計算部分を完成）。
- ExecutionEngine / Broker 実装（モック・本番ブローカーの細部実装とテスト）。
- 監視・アラート（LINE 通知等）の追加強化と E2E テスト。
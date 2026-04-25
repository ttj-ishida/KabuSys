# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。  
リリース日時はコードベースの最終更新内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-25
初回リリース。システム全体の起動スクリプト、設定管理、監視・実行エンジン周り、ポートフォリオ構築ロジック、ユーティリティ、および検証/レポートツールを含む基本機能を提供します。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用に専用 SQLite(DB) を使用し、本番 DB と分離して動作。
    - 停止フラグ（data/stop_requested.flag）検出による安全な停止処理を実装。
    - 実行中の PID を data/execution.pid に記録する機構（Engine 側の pid_file を利用）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: システム監視用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する挙動を明示。
    - 停止フラグ検知・例外時のログ出力・リソースクローズを適切に処理。

- 設定管理 / CLI
  - config.py: 環境変数管理クラス Settings を追加。
    - .env 自動ロード機能を導入（.env / .env.local）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種環境変数の取得メソッドを提供（DBパス、APIトークン、監視閾値、環境種別等）。
    - paper_trading 用の PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH をサポート。PAPER_FILL_MODE のバリデーション実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 秘匿値のマスク表示や選択肢、デフォルト値をサポート。生成した .env をファイルに保存。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および YAML パース検証（PyYAML が存在する場合）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 監視関連
  - monitoring_db 初期化呼び出しを実行スクリプトで行い、監視テーブルの存在を保証（冪等）。
  - SystemMonitor の check_once 呼び出しをポーリングループで運用。例外時にログにスタックトレースを出力して次のポーリングへ復帰。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア順ソートと上位 N 選抜。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア全ゼロ時は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を防ぐフィルタ（売却予定銘柄はエクスポージャー計算から除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め、最大ポジション制約、aggregate cap（利用可能現金に基づくスケーリング）および残差配分ロジックを実装。
    - cost_buffer を考慮した保守的コスト見積りとスケーリング処理。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 環境変数や引数により挙動を上書き可能。既存ハンドラのクリアを行い二重登録を防止。
  - utils/process_priority.py: プラットフォームに依存しないプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX(nice) を吸収し、set_process_priority("high"|"normal"|"low") を提供。
    - CPU affinity 設定用の set_cpu_affinity を提供。アクセス権限や未対応環境でのフォールバックを考慮。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg, max, P95）等を集計して判定（PASS/FAIL）。
    - デフォルト DB は data/paper_trading.db、期間フィルタ（--from, --to）と --db オプションをサポート。
    - 各指標の閾値はファイル上に定義（稼働率 99% 等）。

- リサーチ
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールを追加（モメンタム、MA200、ATR、出来高等を算出する設計）。（実装中のファイルが存在）

### Changed
- なし（初回リリースにつき過去との差分なし）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数ファイル (.env) を Git にコミットしないよう注意書きが config_setup に含まれる。

---

補足（既知の設計上の注意点 / TODO）
- apply_sector_cap: price_map に価格が存在せず 0.0 の場合、エクスポージャーが過少見積りされる可能性があり、コメントで将来的なフォールバック（前日終値等）を検討する旨が記載されています。
- factor_research.py は実装途中で切れている箇所があり（ファイル末尾近辺で中断）、追加実装や単体テストが必要です。
- run_monitoring は監視に常に production sqlite_path を使う設計のため、運用時は設定内容を理解した上で環境変数を適切に設定することを推奨します。
- process_priority / set_cpu_affinity は環境によって権限が必要なため、権限不足時に警告ログを出してスキップする挙動になっています。

--- 

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴・変更履歴とは異なる可能性があります。必要に応じてプロジェクトのコミットログやリリースノートと照合してください。
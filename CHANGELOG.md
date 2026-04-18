CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
リリース日付はソースコードから推測して設定しています（目安）。

[Unreleased]
------------

- ドキュメントや README への追記、マイナーなコメント修正など（内部改善）。

[0.1.0] - 2026-04-18
-------------------

Added
- コア機能を初期実装
  - 実行エンジン起動スクリプト: run_execution.py
    - ExecutionEngine をスレッドで起動し、data/execution.pid に PID を書き込む仕組み。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）を検出して安全に停止する処理を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）を組み込み、初期ポートフォリオ値は broker.get_available_cash() を使用。
  - 監視ポーリング起動スクリプト: run_monitoring.py
    - SystemMonitor を使ったポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を調整可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計（ソース中コメントに明記）。
    - 停止フラグ検出／KeyboardInterrupt による安全終了をサポート。
  - 環境設定関連 CLI
    - config_setup.py: 対話式ウィザードで .env を生成／更新するツールを追加（シークレットのマスク表示、既存値の再利用）。
    - validate_config.py: .env および config/*.yaml のプリフライト検証ツールを追加（--strict オプションで警告を FAIL 扱いにできる）。
  - Paper Trading 検証ツール: tools/paper_verification_report.py
    - paper_trading DB を解析して稼働率／注文成功率／レイテンシ等を集計し PASS/FAIL レポートを出力。
    - P95 計算、各種閾値（稼働率, 成功率, レイテンシ）を定義。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）, 等額配分, スコア加重配分を実装。
    - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）, レジーム乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 各銘柄の発注株数算出（risk_based, equal, score 対応）、単元株（lot_size）対応、aggregate キャップによるスケーリング。
  - 研究用ファクター計算開始
    - research/factor_research.py: Momentum/MA/ATR 等を計算する枠組みを実装（DuckDB 接続を前提）。（一部実装は継続開発中）
  - ユーティリティ
    - utils/logging_setup.py: 共通ロギング設定（stdout StreamHandler + 日次ローテーションファイルハンドラ）を追加。ログディレクトリ自動作成、既存ハンドラのクリアなどを実装。
    - utils/process_priority.py: psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows/Linux/Mac 対応）と CPU affinity 設定ユーティリティを追加。
  - パッケージ初期化
    - kabusys.__version__ = "0.1.0" を設定。

Changed
- .env 自動読み込みの挙動
  - プロジェクトルート (.git または pyproject.toml) を基準に .env/.env.local を自動ロード。既存 OS 環境変数は保護され、.env.local は上書きモードで読み込まれる（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
  - .env のパース機構を強化（export プレフィックス対応、クォート内バックスラッシュエスケープ、インラインコメントの処理）。
- ロギング
  - 既存ハンドラがある場合は一旦 flush/close のうえ削除してから再設定することで二重出力を防止。
  - 標準出力は stdout を使用（stderr ではない） — cron 等でのリダイレクト運用を考慮。
  - ログディレクトリ作成に失敗した場合はファイル出力を切ってコンソールのみで継続する安全動作を採用。
- DB 接続／初期化
  - 起動スクリプト内で監視用テーブルの初期化を idempotent に行う（init_monitoring_db を使用）。
  - DuckDB / SQLite を併用する設計を明確化（分析用は DuckDB、監視／トランザクションは SQLite）。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL の値検証を追加（1 未満や不正値はデフォルトにフォールバックし警告を出す）。

Fixed
- .env パースの不具合対策
  - 空行やコメント行の扱い、export 形式、クォート内エスケープ、インラインコメントの誤解釈を改善。
- プロセス優先度設定の失敗時に例外で落ちないようにキャッチして警告へフォールバック。
- logging_setup でログディレクトリ作成やファイルハンドラ生成に失敗した際の例外ハンドリングを強化。
- 多数の箇所で DB が存在しない・テーブルが無い場合に安全に N/A / 0 を返すガードを追加（tools/paper_verification_report.py の各クエリ等）。
- ExecutionEngine スレッド停止ロジックを改善し、停止フラグ検知時に engine.stop() を呼んでから join するようにした。

Security
- 必須環境変数の明示化とチェックを追加
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config による起動前検証で未設定をエラーとして検出。
- .env の取り扱いに関する注意喚起を config_setup のヘッダに追加（.env を Git にコミットしないこと）。

Deprecated
- なし（初期リリース）

Removed
- なし（初期リリース）

Notes / Migration
- 必須環境変数
  - 環境変数 JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を必ず設定してください。未設定の場合は validate_config でエラーになります。
- 監視 DB の取り扱い
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データを分離したい場合は sqlite_path を適切に設定してください。
- ペーパートレード
  - PAPER_TRADING_SQLITE_PATH（環境変数）またはデフォルト data/paper_trading.db を使用して paper_trading を完全に本番 DB から分離しています。paper_trading モードを使う場合は .env の KABUSYS_ENV を paper_trading に設定してください。
- ログ
  - デフォルトログディレクトリは logs/、アプリ名ごとに日次ローテートされます。必要に応じて LOG_DIR 環境変数で上書きしてください。
- MONITOR_POLL_INTERVAL
  - 監視間隔を秒単位で環境変数 MONITOR_POLL_INTERVAL にて変更できます（1 以上の整数）。不正な値や 1 未満の値は 60 秒にフォールバックします。
- 実装継続中の箇所
  - research/factor_research.py 等、分析・研究系のモジュールは引き続き実装・調整中です。API や戻り値の安定性には注意してください。

参考: 主なコマンド
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ポーリング起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もし特定の変更点（ファイルや機能ごとの詳細な差分）を優先して反映したい場合は、対象コミットや変更前後のファイル一覧を提供してください。さらに正確な CHANGELOG を生成します。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリポジトリ内のバージョン番号（src/kabusys/__init__.py の __version__）およびコード内容から推測して設定しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-20
初回リリース — KabuSys 基本機能を実装しました。主に自動売買エンジンの起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ群、検証ツールなどを含みます。

### 追加 (Added)
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db をデフォルト）へ記録することで本番 DB と分離。
    - 実行中は execution.pid を用いる。停止フラグ（data/stop_requested.flag）を検出して安全停止。
    - 実行中はプロセス優先度を "high" に設定するユーティリティを呼び出す。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - Monitoring は環境に関係なく本番用 sqlite_path を使用する（仕様として明示）。
    - 停止フラグを検知してループ終了、check_once() の例外はログに記録して次ポーリングへ継続。

- 設定管理
  - config.py: 環境変数ラッパー Settings クラスを追加。
    - .env/.env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml が存在する場所）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須値取得用 _require()、各種パス・閾値・フラグ・環境切替（development / paper_trading / live）などをプロパティで提供。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - paper_sqlite_path、duckdb_path、sqlite_path 等のデフォルトを設定。

- 設定関連 CLI
  - config_setup.py: 対話形式で .env を作成・更新するウィザードを追加。
    - J-Quants や kabuAPI 等の必須項目を含むテンプレートと保存機能。
  - validate_config.py: 起動前に .env と config/*.yaml の状態を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば検証）。
    - --strict モードにより警告を FAIL として扱うオプションを追加。
    - 本番環境 (KABUSYS_ENV=live) に対する追加ガード（LINE 通知の有無、KILL_FLAG_CLEAR_ON_START の警告）。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート／選抜。
    - calc_equal_weights: 等配分重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを基に新規候補を除外）。
    - calc_regime_multiplier: マーケットレジームに応じた投下比率乗数（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算（risk_based / equal / score 対応）、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り。

- 研究・ファクター計算基盤
  - research/factor_research.py: DuckDB を用いたファクター計算基盤の実装を追加（モメンタム・MA200・ATR 等の計算方針を実装中の箇所あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - paper_trading DB（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler）を併用。ログディレクトリ作成失敗時はファイル出力をスキップし警告。
    - LOG_LEVEL / LOG_DIR の環境変数と関数引数による上書き。
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定および CPU affinity 設定を追加（psutil ベース、例外は警告でスキップ）。

- 監視用 DB 初期化 API（冪等）
  - monitoring/monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証（run_* スクリプトから利用）。

### 変更 (Changed)
- パッケージメタ
  - src/kabusys/__init__.py にバージョン番号 __version__ = "0.1.0" を設定。

### 修正 (Fixed)
- 監視ループ・例外耐性
  - run_monitoring のポーリング中に monitor.check_once() が例外を投げた場合、例外を捕捉してログ出力後に次ポーリングへ継続するように実装（単一障害によるループ停止を回避）。

### 破壊的変更 (Breaking Changes)
- 監視 DB の参照挙動
  - run_monitoring は KABUSYS_ENV の値にかかわらず常に Settings.sqlite_path（本番監視 DB）を使用する仕様です。監視用途に別 DB を使いたい場合は実装上の考慮が必要です。
- PAPER_TRADING と本番 DB の分離
  - paper_trading モードでは paper_sqlite_path を使うため、paper_trading のデータはデフォルトで data/paper_trading.db に隔離されます。既存の環境で別挙動を期待している場合は設定の調整が必要です。

### セキュリティ関連 (Security)
- .env の自動ロードは OS の環境変数を保護する設計
  - .env/.env.local 読み込み時に既存の OS 環境変数はデフォルトで上書きされない（.env.local は override=True だが protected により OS 環境変数は上書きされない）。
  - 必須環境変数が未設定の場合は validate_config で明示的にエラーを出力する。

### 既知の制約・注意点 (Known issues / Notes)
- process_priority / cpu_affinity はプラットフォームと権限に依存し、設定に失敗した場合は警告ログを出して処理を継続します。
- portfolio.position_sizing の価格データ欠損時の扱いに注記あり（コメント中の TODO）。価格が 0.0 の場合、エクスポージャーや発注量が過少見積もられる可能性があるため、将来的にフォールバック価格の導入を検討。
- research/factor_research.py はファクター計算方針を実装中の箇所がある（ファイル末尾が途中で切れているため、追加実装が必要）。

---

（注）
- この CHANGELOG はリポジトリ内のソースコードから実装内容を推測して作成したものであり、実際のリリースノートや仕様書に基づくものではありません。必要に応じて内容の追記・修正を行ってください。
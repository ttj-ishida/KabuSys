# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回公開リリース。

### 追加 (Added)
- 起動スクリプトを追加
  - run_execution.py：ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合はペーパートレーディング用の MockBrokerClient を利用し、専用 SQLite（デフォルト: data/paper_trading.db）に記録する。停止フラグ検出によるグレースフルな停止処理、PID ファイル管理、スレッドでのエンジン実行を実装。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
- 設定・環境管理
  - config.py：.env の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）、.env の詳細なパース（export プレフィックス、クォート・エスケープ、インラインコメント処理）を実装。Settings クラスでアプリ設定のプロパティ化（検証付き）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - config_setup.py：対話式ウィザードで .env を初期作成・更新する CLI を追加（python -m kabusys.config_setup）。
  - validate_config.py：起動前に .env と config/*.yaml を検証する CLI を追加。--strict モードで警告を FAIL 扱いにできる。PyYAML が無ければ YAML の検証はスキップし警告表示。
- ログ・ユーティリティ
  - utils/logging_setup.py：共通のログ設定ユーティリティ。コンソール（stdout）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py：プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を提供（psutil 利用）。Windows / POSIX（Linux, macOS 等）対応。権限不足等で安全にフォールバック。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py：シグナル選定（select_candidates）、等金額・スコア重みの計算（calc_equal_weights, calc_score_weights）を追加。スコア全ゼロ時のフォールバックとログ警告あり。
  - portfolio/risk_adjustment.py：セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を追加（既定: bull/neutral/bear マッピング）。
  - portfolio/position_sizing.py：銘柄ごとの発注株数計算 calc_position_sizes を追加。risk_based / equal / score の複数配分方式に対応、lot_size（単元）丸め、max position / aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積もりを実装。
  - portfolio/__init__.py に上記を公開。
- ツール
  - tools/paper_verification_report.py：ペーパートレーディングの検証レポート生成ツールを追加。期間指定の CLI オプションあり（--from/--to/--db）。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力する。P95 計算を実装し、デフォルト閾値を設定（稼働率 >=99%、注文成立率 >=90%、送信率 >=95%、P95 <=200ms）。

### 変更 (Changed)
- ログの標準出力先を stderr ではなく stdout に統一（cron/Task Scheduler 等からのリダイレクトを想定）。
- .env の読み込みルールを明確化（OS 環境変数を保護する protected セット、.env.local による上書き）。
- run_monitoring と run_execution が起動時にプロセス優先度を "high" に設定するようにした（set_process_priority を利用）。
- run_execution が起動前に監視用 DB テーブル（監視テーブル）を冪等に初期化するため init_monitoring_db を呼ぶようにした（監視ログの整合性確保）。

### 修正 (Fixed)
- .env パーサーの以下の改善・堅牢化
  - export プレフィックスの対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの正しい無視処理を実装。
  - 空行やコメント行を正しくスキップ。
- run_monitoring のポーリング間隔取得ロジックで不正値（0 以下や非整数）を検知した際にデフォルトへフォールバックし、警告ログを出すようにした（time.sleep に渡す不正値回避）。
- process_priority / set_cpu_affinity：権限不足や未対応プラットフォームで安全に警告を出してスキップするように改善。
- calc_score_weights：全銘柄のスコアが 0 の場合に等金額配分にフォールバックするようにし、警告ログを出すようにした。
- calc_position_sizes：aggregate cap を満たさない場合にスケールダウンし、lot_size 単位での丸めと端数配分アルゴリズムを導入して合計投資額が available_cash を超えないようにした。

### ドキュメント（補足） (Documentation / Notes)
- Settings クラスで環境変数の検証を行うため、KABUSYS_ENV や PAPER_FILL_MODE、LOG_LEVEL 等に不正な値を設定すると起動時に例外を発生させる可能性がある。validate_config CLI を使用して事前検証を推奨。
- monitoring は設計上「監視データ用 DB」を常に本番 sqlite_path に書き込む仕様とした（開発環境での動作確認時は注意）。
- Paper Trading の検証・実行は本番環境データベースと分離されるよう paper_sqlite_path を用意。PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。

### 既知の制限 / TODO
- position_sizing の price フォールバックが未実装（price が欠損した場合の見積り改善は将来的な TODO）。
- research.factor_research モジュールは大枠を実装中（ファイル終端が途中で切れている箇所あり）。将来的にファクター計算の完全実装を予定。

## 参考（コマンド）
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

――以上。
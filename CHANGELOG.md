CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリースを作成。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV による paper_trading と live の切替をサポートし、ペーパートレード時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用する。停止フラグ（data/stop_requested.flag）検知や PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定・環境管理:
  - config.py: .env の自動読み込み（プロジェクトルート自動検出）、.env パース（export 形式、クォート、インラインコメント等に対応）、必須キー取得ヘルパー、各種設定プロパティ（DB パス、paper_trading 用パス、閾値、環境種別判定など）。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加（秘密項目マスク、デフォルト・選択肢対応、保存確認）。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を追加（--strict オプション、YAML パースチェック、live 時のガードチェック等）。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテーションのファイルハンドラを統一的に設定するユーティリティ。ログディレクトリ自動作成、既存ハンドラのクリーンアップ、LOG_LEVEL/LOG_DIR による上書き。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティ（Windows/Linux/macOS 対応の抽象化）。権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築関連:
  - portfolio/portfolio_builder.py: シグナル選別（score 降順、signal_rank によるタイブレーク）、等金額配分とスコア加重配分を実装。スコア合計が 0 の場合はフォールバックで等配分。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。allocation_method（"risk_based" / "equal" / "score"）に対応。単元株丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料/スリッページ見積り）等を考慮。
  - portfolio/risk_adjustment.py: セクター集中制限（既存保有比率が閾値を超える場合に同一セクターの新規候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームや unknown セクターのフォールバック挙動を明示。
  - portfolio/__init__.py: 上記機能をパッケージとして公開。
- リサーチ・ファクター計算（基盤実装）:
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 系の計算方針を実装開始。モメンタム計算のための定数や設計方針が記載（コードは一部実装・続きあり）。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 結果を検証するレポート生成ツールを追加。稼働率、注文成功率、送信率、API レイテンシ（P95）等を集計し PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。閾値や P95 算出、日付フィルタ (--from/--to) をサポート。
- パッケージメタ:
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため過去変更はなし）設計上の注意点をドキュメント文字列やログに明記（例: monitoring は本番 sqlite を使う点、.env 自動ロードの挙動、ログディレクトリ作成失敗時のフォールバック等）。

Fixed
- N/A（初回リリース）

Security
- 機密情報取り扱いの配慮:
  - config_setup のウィザードでシークレット項目は表示マスク。
  - .env は「絶対に Git にコミットしないこと」を README/ヘッダで明記（.env 書き込みテンプレートに注記）。

Notes / 注意事項
- run_monitoring は停止フラグ（data/stop_requested.flag）でループを抜ける仕様。MONITOR_POLL_INTERVAL に不正値が与えられた場合は警告を出してデフォルト 60 秒にフォールバックします。
- run_execution は停止フラグ検知時に ExecutionEngine.stop() を呼び出して安全停止を試みます。ペーパートレード時は BrokerClientFactory により MockBrokerClient を利用することを想定。
- config.py の自動 .env ロードはプロジェクトルートが特定できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップします。
- position_sizing のスケーリングや価格欠損時の挙動は注意が必要（コード内に TODO やログ出力あり）。特に price が 0 の場合はスキップされ、エクスポージャー過小見積りにつながる可能性があります。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

----
This project adheres to "Keep a Changelog" — and aims to make release notes clear and accessible.
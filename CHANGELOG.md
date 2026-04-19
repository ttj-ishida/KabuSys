CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初期リリース。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプト。環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient と本番 DB を分離する仕組みを実装。停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出時に安全に終了。
- 設定・環境管理
  - config.py: .env 自動ロード機能（.env, .env.local をプロジェクトルートから読み込み、OS 環境変数を保護する実装）。各種設定プロパティ（DB パス、KABUSYS_ENV 判定、PAPER_FILL_MODE、閾値など）を提供。
  - config_setup.py: .env 初期作成・更新を対話式で行うウィザード CLI を提供。シークレット項目はマスク表示。
  - validate_config.py: 起動前に必須環境変数や config/*.yaml の存在・簡易パースを検証する CLI。--strict オプションで警告を FAIL 扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出力。
- DB / 分析
  - DuckDB と SQLite の両方をサポートする実行フロー（Settings でパス指定）。監視テーブル初期化ユーティリティを呼び出して冪等に監視 DB 準備を行う。
- ロギングと運用ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout） + TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定する共通ユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティ（Windows/Linux/macOS 対応の範囲で実装）。CPU affinity 設定関数も提供。権限不足などの失敗は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク処理）、等金額配分、スコア加重配分（合計スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバック挙動あり）。
  - portfolio/position_sizing.py: allocation_method（"risk_based", "equal", "score"）に基づく株数決定ロジックを実装。単元（lot_size）丸め、per-position 上限、aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウン・再配分ロジックを含む。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。期間フィルタ（--from / --to）と --db による DB 指定をサポート。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL 判定を行う。
- 研究モジュール（初期実装）
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を設計・部分実装。DuckDB の prices_daily / raw_financials を使う設計で、モメンタム（1M/3M/6M）や MA200 乖離などを計算する関数を用意（ファイル末尾は作業中の箇所あり）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- config_setup.py にて .env ファイルにシークレットを格納する際、ウィザード中は入力値をマスクして表示。README レベルの注意書きとして .env を Git にコミットしないことを出力。

Notes / Implementation details
- run_monitoring と run_execution はそれぞれ停止フラグ（data/stop_requested.flag）を監視して安全終了する仕組みを採用。
- Settings.paper_fill_mode は有効値検査を行い、不正値なら ValueError を送出する。
- .env のパース実装はクォートあり・エスケープ対応、インラインコメント処理など堅牢に実装されている。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出すため、環境に依存しない実行が可能。
- process_priority の設定は権限不足や未対応 OS での失敗を安全にハンドリング（警告を出してスキップ）。
- ロギングは stdout を標準出力に使う設計（cron 等で stdout/stderr を一本化しやすくするため）。

開発/今後の予定（Work in progress）
- research/factor_research.py の計算処理（ファイル末尾が途中）を完成させ、テスト・ドキュメントを追加する予定。
- 各コンポーネント（ExecutionEngine, SystemMonitor, BrokerClient 等）のユニットテスト追加と統合テストの整備。
- 単元株数（lot_size）を銘柄別に扱えるよう stocks マスタや銘柄別 lot_map への対応検討。

署名
- バージョンはパッケージ内 __version__ = "0.1.0" に合わせています。
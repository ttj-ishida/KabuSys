# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはコードベースの現状から推測して作成した初回リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 実行/監視用のエントリポイントスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、ExecutionEngine のバックグラウンド実行・停止監視を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - 実行停止はプロジェクトルート/data/stop_requested.flag によるフラグ検出で行う。PID を data/execution.pid に格納。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用し、監視 DB 初期化処理を実行。
    - 停止フラグ検出によりループを終了。KeyboardInterrupt による終了もハンドリング。

- 設定関連
  - config.py: 環境変数読み込み・管理モジュールを実装。
    - プロジェクトルート（.git または pyproject.toml を起点）を自動検出し .env/.env.local を自動読み込み（OS 環境変数を保護）。
    - export KEY=val 形式、クォート内エスケープ、インラインコメントなどを考慮した .env パーサーを実装。
    - Settings クラスで各種設定値（パス、閾値、API トークン等）をプロパティとして提供。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。シークレット項目はマスク表示。生成ファイルのテンプレート書き出しを行う。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML 有無によりスキップ）をチェック。--strict オプションで警告も FAIL 扱い。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等分配 / スコア重み）を実装。スコア合計が 0 の場合は等金額配分にフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。
    - risk_based, equal, score の配分方式に対応。
    - lot_size（単元株）丸め、1銘柄上限・アグリゲート上限、cost_buffer による保守的見積り、残差処理による再配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用および市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。

- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一セットアップを実装。stdout 向け StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/, 30 日保持）を設定。ログレベル/ディレクトリは引数・環境変数で解決。既存ハンドラのクリーンアップ機能付き。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS 等の差分を吸収して安全にフォールバックする実装。権限不足等は警告でスキップ。

- モニタリング DB 初期化ユーティリティを導入（monitoring.monitoring_db.init_monitoring_db を使用）
  - 監視テーブルが存在することを保証する冪等な初期化処理呼び出しを run_monitoring/run_execution から行う。

- Paper Trading 向けツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を SQLite の監視ログ / trade_logs / risk_logs から集計して判定（PASS/FAIL）を出力。
    - 各指標の閾値（例: 稼働率 >= 99%、P95 <= 200 ms）を定義。
    - --from/--to/--db オプションで期間・DB を指定可能。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- none（初回リリース想定のため差分は無し）

### Fixed
- none（初回リリース想定のため差分は無し）

### Removed
- none

### Security
- none

## [0.1.0] - 2026-04-19

初回リリース。上記「Added」に記載した機能群をまとめてリリース。

- 実行・監視エントリポイント (run_execution, run_monitoring)
- 設定管理とウィザード (.env 自動読み込み, config_setup, validate_config)
- ロギング・プロセス優先度ユーティリティ
- ポートフォリオ構築ライブラリ（候補選定・配分・ポジションサイズ・リスク調整）
- Paper Trading 向け検証レポートツール
- 監視 DB 初期化ユーティリティ呼び出し
- パッケージメタ情報 (__version__ = 0.1.0)

注意事項・既知の制約
- config.auto-load の仕組みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後は自動検出が失敗する可能性があるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を用意すること。
- process_priority / set_cpu_affinity の一部機能は権限やプラットフォームによって無視される場合がある（警告を出力して継続）。
- portfolio/position_sizing の価格フォールバックは現状未実装（price が欠損時の挙動について TODO コメントあり）。
- research/factor_research.py のモメンタム計算関数は実装を開始しているが、ファイル末尾が途中（未完）であるため完全実装が必要。

---

この CHANGELOG はコードリポジトリの現状から推測して作成しています。追加のコミット履歴やリリース日付、変更者情報などが利用可能であれば、より正確な履歴と日付の適用を推奨します。
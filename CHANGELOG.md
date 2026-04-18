# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルは、コードベース（src/ 以下）の現在の状態から推測して作成しています。

なおバージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に合わせています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-18
初期リリース — 基本的な自動売買フレームワークのコア機能を実装。

### Added
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使い MockBrokerClient を利用する想定。起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する作り。
  - validate_config.py: .env や config/*.yaml の設定整合性をチェックする CLI を追加（--strict オプションで警告を失敗扱いにできる）。必須環境変数やパス存在、YAML のパースチェック、ライブ環境特有のガード等を実装。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）をガイドしてファイル書き出しする。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数をまとめて判定（PASS/FAIL）する。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。

- 設定管理
  - config.py: Settings クラスを実装。環境変数の読み取りラッパーを提供し、デフォルト値・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。プロジェクトルート自動検出に基づく .env 自動読み込み（.env → .env.local、OS 環境変数は保護）機能を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの細かい仕様（export プレフィックス、クォートやエスケープ、行内コメントの扱い）に対応。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み計算（calc_equal_weights、calc_score_weights）を追加。スコアが全て 0 の場合は等配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知のレジーム時はフォールバック処理あり。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。allocation_method として "risk_based" / "equal" / "score" をサポートし、単元株（lot_size）丸め、1銘柄上限・合計利用上限（aggregate cap）のスケーリングロジック、コストバッファ（手数料・スリッページ見積）を考慮した配分アルゴリズムを備える。

- データ処理・リサーチ
  - research/factor_research.py（骨組み・仕様記述）: DuckDB 接続を受け取り、prices_daily / raw_financials テーブルからモメンタム等のファクターを計算する設計を追加（関数の説明や定数、計算対象日数を定義）。P95 計算やスキャン幅の定義などを含む（実装の続きが期待される箇所あり）。

- DB / 分析基盤
  - DuckDB 統合: run_* スクリプトや各コンポーネントで duckdb に接続するようになっている（Settings.duckdb_path）。
  - monitoring DB 初期化フック: init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を追加。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール (stdout) と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成の挙動、環境変数によるログレベル/ディレクトリの解決順を実装。
  - utils/process_priority.py: Windows/Linux/macOS に跨るプロセス優先度設定ユーティリティを追加。nice 値・Windows 優先度クラスを抽象化し、失敗時は警告でスキップ。CPU affinity 設定関数も提供。
  - utils/__init__.py を整備。

- 実行コンポーネント構成（Engine 等）
  - execution パッケージの起動時依存関係（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager）を組み立てるロジックを run_execution に追加。RiskConfig のデフォルト値やレート制限・サーキットブレーカー等の初期設定を含む。

### Changed
- none（初期リリースのため変更履歴は追加のみ）

### Fixed
- none（初期リリースのため）

### Notes / 注意点
- run_monitoring は意図的に KABUSYS_ENV に関係なく本番用の sqlite_path を使用する挙動になっているため、開発環境で実行する場合は SQLITE_PATH の設定に注意すること。
- run_execution は paper_trading モードで paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを分離する設計になっている。
- .env の自動ロードでは OS 側の既存環境変数を保護するための仕組みがあり、テストなどで自動ロードを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- config_setup.py と validate_config.py により、導入時のセットアップ / 検証を CLI ベースで行える。validate_config の --strict を併用すると警告を失敗扱いできるため、デプロイ前チェックに便利。
- PAPER_FILL_MODE、MONITOR_POLL_INTERVAL、KILL_FLAG_CLEAR_ON_START などの環境変数による挙動変更があるのでドキュメントやデプロイ設定での反映を忘れないこと。

---

タグ:
- Unreleased
- 0.1.0

（必要に応じて将来的なリリースごとに本ファイルを更新してください）
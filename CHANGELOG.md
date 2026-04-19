CHANGELOG
=========

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本機能を実装。
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - 高度な .env パーサ実装（export 形式・クォート付き値・インラインコメント処理に対応）。
  - Settings クラスを導入し、環境変数経由でアプリ設定を取得可能に。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI を追加。
- 実行・監視起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB を使用（data/paper_trading.db）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグ / PID ファイルにより安全にプロセス停止・管理可能。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: コンソール（stdout）および日次ローテーションファイルハンドラを備えた統一ログ設定ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（nice / 高優先度クラス）と CPU affinity 設定を追加。権限不足時は警告を出してスキップ。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder: 候補選定と等重・スコア重み計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: リスクベース / 等配分 / スコア配分に基づく株数決定ロジックを実装（lot 単位丸め・aggregate cap スケーリング・cost_buffer を考慮）。
  - portfolio パッケージの公開 API を整備。
- リサーチ / ファクター計算（初期実装）
  - research.factor_research: DuckDB 接続を受け取り prices_daily 等のテーブルからモメンタム等を計算する基盤実装（設計・定数定義、calc_momentum の骨格）。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を解析して稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL レポートを出力するスクリプトを追加。期間フィルタや DB パス上書きオプションをサポート。
- DB サポート
  - duckdb / sqlite を利用したデータアクセスを前提に実装。Monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）を各起動処理で呼び出し、テーブル存在を保証する設計。

Changed
- なし（初回リリースのため変更履歴なし）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Breaking Changes / 注意事項
- Settings クラスは KABUSYS_ENV や LOG_LEVEL、PAPER_FILL_MODE 等の値検証を行い、不正な値の場合は ValueError を送出します。起動スクリプトや運用環境でこれらの環境変数を設定する際は有効値に従ってください。
- run_monitoring は「監視用 SQLite パス」に関して環境にかかわらず本番 sqlite_path を使用する実装意図があります。運用時には対象 DB パスを確認してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と分離します。ペーパートレードと本番の DB を同一にしないよう注意してください。
- process_priority と CPU affinity の設定は psutil に依存し、プラットフォームや権限によって挙動が変わるため、期待通り動作しない場合はログの警告を確認してください。
- .env の自動読み込みはデフォルトで有効（プロジェクトルートが検出できる場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向けメモ
- 各 CLI はモジュール実行（python -m kabusys.<module>）で起動可能。ログ設定・PID/停止フラグ・DB 初期化は各スクリプトで一貫して行われます。
- Portfolio / Position sizing / Risk modules は副作用のない純粋関数として実装されているため単体テストが容易です。
- DuckDB を用いたリサーチ処理は SQL と Python の組合せで設計されており、prices_daily / raw_financials テーブルのスキーマが前提です。

今後の予定（例）
- research モジュールの各ファクター計算の実装完了（volatility, value, liquidity 等）。
- ExecutionEngine / BrokerClient の統合テストやモックを用いたシミュレーションカバレッジ拡充。
- マルチ銘柄の lot_size を銘柄別に扱う拡張（stocks マスタ導入）。
- 運用用のドキュメント・デプロイ手順の整備。
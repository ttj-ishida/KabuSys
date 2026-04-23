CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリースを追加。
- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用 DB（data/paper_trading.db）と MockBrokerClient を使う挙動をサポート。エンジンはスレッドで実行され、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化・DuckDB 接続を行い停止フラグ検知でループを終了。
- 設定関連
  - config.py: Settings クラスを導入。.env 自動ロード（.env → .env.local の優先順）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、quoted value や inline comment に対応した .env パーサーを実装。各種設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等）をプロパティで提供し、不要な値は例外を送出して早期検出。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を行う CLI を追加（項目一覧・保存ロジック・既存値再利用機能）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML が無ければ警告）や本番環境用の追加ガードを実装。--strict フラグで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を提供。スコアが全て 0 の場合に等配分へフォールバックする警告を出す。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull","neutral","bear" をマップ、未知レジームはフォールバック）。
  - portfolio.position_sizing: calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポートし、単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料/スリッページ想定）等を考慮した発注株数計算ロジックを提供。
- モニタリング / データベース
  - monitoring_db 初期化呼び出しを各起動処理に組み込み。SystemMonitor は sqlite と duckdb の両方を利用可能。
  - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL からの解決、既存ハンドラのクリーンアップを行う。
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、アクセス権限がない場合は警告でフォールバックする実装。
- ツール
  - tools.paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ（P95 を含む）等を集計し、閾値に基づく PASS/FAIL レポートを生成するスクリプトを追加。閾値はソース内で定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
- 研究用モジュール（着手）
  - research.factor_research: モメンタム・ボラティリティ等のファクター計算モジュールを追加（DuckDB の prices_daily / raw_financials を参照する設計、モジュールの計算関数を準備。モジュールはさらに実装拡張予定）。
- パッケージ情報
  - __init__.py: パッケージバージョンを 0.1.0 に設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記
- 多くのモジュールは DB（SQLite/DuckDB）や外部ブローカーへの接続を想定しており、本番運用前に .env の設定と validate_config による検証を推奨します。
- .env ファイルは生成・保存・取り扱いに注意し、絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きあり）。

今後の予定（短期的）
- research.factor_research の残実装（指標計算の完成化）
- 単体テストの追加、CLI の使い勝手向上
- 監視/実行コンポーネントのさらなる堅牢化（再試行/アラート強化）
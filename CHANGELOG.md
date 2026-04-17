# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys の基本モジュールと CLI / ツール群を追加。
- 環境設定・管理
  - Settings クラスを導入し、環境変数経由で各種設定（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境など）を取得可能に。
  - .env 自動読み込み機能を追加（プロジェクトルートの .env/.env.local を優先的にロード）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env 読み込みのための堅牢なパーサを実装（コメント、クォート、export 形式に対応）。
  - 環境設定ウィザード CLI を追加（python -m kabusys.config_setup）。対話式で .env を作成・更新できる。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数や config/*.yaml、パスの存在チェック、production 向けガードを実施。--strict モードをサポート。
- 実行・監視ランナー
  - run_execution スクリプトを追加。ExecutionEngine を立ち上げるエントリポイント。プロセス優先度設定、paper_trading 用の専用 SQLite 分離（data/paper_trading.db 想定）、停止フラグ（data/stop_requested.flag）による安全停止、実行 PID ファイル管理を実装。
  - run_monitoring スクリプトを追加。SystemMonitor をポーリング実行するエントリポイント。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境に依らず本番 sqlite_path を使用。
- 監視・実行基盤
  - 監視 DB 初期化呼び出し（init_monitoring_db）と DuckDB 接続を組み込み、冪等に監視テーブルを保証。
  - 停止フラグと PID 管理、例外発生時のログ出力と安全なクローズ処理を実装。
- Broker / Execution サポート
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を想定）。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て・起動処理を組み込み（EngineConfig, RiskConfig を使用）。
  - RiskManager の初期設定例（max_position_pct, max_utilization, rate_limit など）を提供し、初期利用可能現金を broker.get_available_cash() から取得。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全ゼロ時は等配分へフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。unknown セクターの扱いやレジーム不明時のフォールバック挙動を定義。
  - position_sizing: position（株数）計算（calc_position_sizes）。risk_based / equal / score の配分方式をサポートし、単元株丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ）考慮、残差に基づく追加配分ロジックを実装。
- リサーチ / ファクター計算
  - research/factor_research モジュールを追加。DuckDB の prices_daily / raw_financials を参照し、Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20 等）、流動性指標などを算出するユーティリティ関数を実装。データ不足時の None 処理を明確化。
- ユーティリティ
  - process_priority ユーティリティを追加（set_process_priority, set_cpu_affinity）。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収し、権限や未サポート環境で失敗してもログ警告を出して継続する設計。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の SQLite（デフォルト data/paper_trading.db）を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算・判定（PASS/FAIL）してレポート出力。期間指定（--from/--to）と DB パスオーバーライドをサポート。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数や .env の取り扱いについて、.env を絶対に Git にコミットしない旨を README/生成ファイルに記載する方針を採用（config_setup に注意書きあり）。

Notes
- 本バージョンは初期実装であり、将来的に以下の拡張や改善が想定されています:
  - 銘柄別の lot_size 管理（stocks マスタ導入）
  - price の欠損時のフォールバックロジック（前日終値や取得原価の利用）
  - 更に詳細な監視テーブル・メトリクスの追加
  - テストカバレッジ拡充およびエラーハンドリングの強化

--------------------------------------------------------------------
（参考）パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応しています。
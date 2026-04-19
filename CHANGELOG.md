# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
初回公開リリースとして、以下の機能群を実装しています（コードベースから推測して記載）。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行・監視プロセス起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続やスレッドでのエンジン実行、停止フラグ検知による安全停止をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループ終了。
- 環境設定・管理機能を追加
  - config.py: .env 自動ロード（プロジェクトルート検出に基づく）、環境変数パースロジック、Settings クラス（各種設定プロパティ）を実装。KABUSYS_ENV（development/paper_trading/live）や paper_trading 用 DB パス、しきい値などを提供。
  - config_setup.py: 対話式 .env ウィザード。初期作成・更新を支援し、テンプレートに基づく書き込みを行う。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにする。
- Execution / Broker 関連の組み立てロジック（起動スクリプト内）
  - BrokerClientFactory を用いて環境に応じたブローカークライアント生成（paper_trading 時は Mock を使用して DB を分離）。
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立ておよび起動制御。
- 監視関連
  - monitoring_db 初期化呼び出しを追加し、監視用テーブルが存在することを保証（冪等）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計を採用（監視データの一元化）。
- ログ・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテーション）を設定するユーティリティを実装。既存ハンドラの二重設定を防止し、LOG_DIR / LOG_LEVEL の解決ロジックを提供。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを実装。権限不足・未サポート環境では安全にスキップする。
- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: ポジションサイズ（発注株数）計算ロジックを実装（risk_based / equal / score 的配分、lot_size/aggregate cap/スケーリング処理等）。
  - portfolio/__init__.py: 上記関数群をパッケージとして公開。
- 研究・ファクター計算基盤を追加（初期）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を追加。モメンタム系関数の計算方針と定数を定義（処理の骨組み・定数は実装済み、関数実装は進行中）。
- ツール類
  - tools/paper_verification_report.py: ペーパートレード用 SQLite （デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。稼働率、注文成功率・送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。日付レンジ指定 (--from / --to) と DB パス指定 (--db) に対応。
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### 変更 (Changed)
- .env 読み込みの挙動を明確化
  - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式、クォート文字・バックスラッシュエスケープ、インラインコメントの扱いに対応し、より堅牢なパースを実現。
- ロギングの挙動
  - ログはデフォルトで stdout に出力（cron / Task Scheduler との運用を考慮）し、logs/<app_name>.log に日次ローテーションでファイル出力（ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続）。
- ExecutionEngine / Monitoring における DB 分離方針
  - Paper Trading 実行時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離するよう変更（起動スクリプトの実装にて）。

### 修正 (Fixed)
- 環境変数取得の堅牢化
  - Settings クラスの各プロパティで不正値の検証を追加（例: PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV / LOG_LEVEL の検証）。
- process_priority の失敗ケースを安全にハンドリング
  - psutil による優先度設定・CPU affinity 設定で AccessDenied / NotImplementedError 等が発生した場合に警告を出してスキップするように修正。
- ポジションサイズ計算の端数処理
  - aggregate cap を超える場合のスケーリング処理で lot_size 単位での丸めと残余キャッシュを用いた追加配分ロジックを実装し、再現性のある配分を行うように改善。

### 既知の制限 / TODO
- research/factor_research.py のモメンタム計算関数等は一部実装が未完（ファイル末尾で実装が中断している箇所あり）。今後、DuckDB を用いた SQL 実装を完成させる必要あり。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少評価されるリスクあり。将来的に前日終値や取得原価でのフォールバック対応を検討中。
- position_sizing:
  - lot_size の銘柄別対応は未対応（全銘柄共通の lot_size を使用）。将来的に銘柄マスタで個別単元対応を追加予定。
- 一部外部依存（PyYAML）がない場合は config/*.yaml の内容検証をスキップする設計になっている。CI / デプロイ環境では必要に応じて依存を整備すること。

---

開発・運用に関する補足:
- Paper Trading と Live の DB は明確に分離され、ペーパートレード検証用のレポート生成ツールを同梱しています。
- 起動スクリプトは停止フラグ（data/stop_requested.flag）や pid ファイル等を用いた簡易的なプロセス管理を想定しています。運用時は systemd / supervisor 等と組み合わせた運用を推奨します。

（本 CHANGELOG はコードの内容およびソース内コメントから推測して作成しています。実際のコミット履歴やリリースノートに応じて適宜更新してください。）
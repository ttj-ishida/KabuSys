Keep a Changelog
=================

すべての注目すべき変更を履歴として残します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-20
-----------------

初回公開リリース。コードベースから推測される主要機能・改善点を記載します。

Added
- 実行スクリプト
  - run_execution.py: 実際の ExecutionEngine を起動するエントリポイント。Paper Trading 環境では MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に分離して記録する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止用フラグファイル（data/stop_requested.flag）を監視して安全に終了する。
- 設定・環境管理
  - config.py: .env 自動読み込み（.env, .env.local の優先度）、.env のパース機能（export 形式、クォート/エスケープ、インラインコメント処理対応）、各種設定プロパティ（DB パス、paper trading 関連、監視しきい値、KABUSYS_ENV 判定等）を提供する Settings クラスを追加。
  - config_setup.py: 対話式の .env 作成/更新ウィザード。必須項目の入力支援、既存値の再利用、保存前確認などの機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml の検証を行う CLI。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスや YAML ファイル存在確認、KABUSYS_ENV=live 時の追加ガードを備える。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ統一的に構成するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: Windows と POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を提供。psutil に依存しつつ例外発生時は警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: シグナルから候補選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバック等を考慮。
  - portfolio/position_sizing.py: 発注株数決定ロジック（allocation_method: risk_based / equal / score）を実装。単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate キャップ付きのスケーリング処理を備える。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 上記機能をまとめてエクスポート。
- Execution 内部コンポーネント（エンジン周り）
  - run_execution.py から組み立てられる各コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を想定した起動フローを実装。RiskManager に既定のリスク設定を与え、ExecutionEngine は別スレッドで実行、フラグファイルで停止制御を行うように設計。
- Monitoring / 診断ツール
  - monitoring 側の DB 初期化ユーティリティ（init_monitoring_db）と SystemMonitor を使用。Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する旨を明示。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の履歴 DB から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計してレポートを出力する CLI。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
- 研究用ファクターモジュール（研究基盤）
  - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算する基盤を追加（モメンタム計算ロジック等を実装開始）。prices_daily / raw_financials テーブルのみ参照する方針。

Changed
- ログの標準出力先を stdout に統一（cron/Task Scheduler 等でのリダイレクト扱いを想定）。
- .env ロードの優先度を OS 環境 > .env.local > .env とし、OS 環境変数を保護する仕組みを導入（protected keys）。
- run_monitoring.py と run_execution.py の起動フローでプロセス優先度を最初に設定するようにした（set_process_priority("high")）。

Fixed
- .env パーサの改善:
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープと閉じクォート検索に対応。
  - クォート無しの場合のインラインコメント認識ルールを改善（'#' の直前に空白がある場合のみコメントとみなす）。
- Logging 設定時に既存ハンドラを適切に flush/close してからクリアするようにして、二重設定やハンドラリークを防止。

Notes / Implementation details
- Paper Trading と Live の DB は分離（paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）。
- monitoring 側は運用上の都合で KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する設計になっている（注意喚起あり）。
- ExecutionEngine の停止は data/stop_requested.flag を用いる。起動時に既にフラグが立っている場合は起動せず終了する。
- position_sizing の aggregate スケーリングは lot_size（単元株）単位で切り捨て／端数処理を行い、残余キャッシュで残差分を再配分するアルゴリズムを採用している。
- リスク設定や閾値等は Settings や各モジュール内でデフォルト値が埋め込まれており、環境変数や将来的な設定ファイルで上書き可能な設計。

Known issues / TODO（コード中コメントからの推定）
- portfolio/risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる可能性があり、前日終値や取得原価でのフォールバックがコメントで示唆されている。
- research/factor_research.py はモメンタム等の計算を含むが、ファイル末尾が途中で切れている（追加実装が必要な可能性）。
- 将来的な拡張として、銘柄ごとの lot_size を stocks マスタで管理する案が示唆されている。

Authors
- コードベースから推測して本リリースの実装は KabuSys 開発チームによるもの。

License
- リポジトリに明示的なライセンスファイルが見当たらない場合、配布/利用前にライセンスを確認してください。

もし CHANGELOG を別の粒度（例: モジュール別、重要度別、セキュリティ修正の分離）で整形したい場合は指示してください。
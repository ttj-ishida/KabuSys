# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初回リリースはコードベースから推測した機能群をまとめたものです。

## [Unreleased]

（現在のところ未リリースの変更点はありません。）

## [0.1.0] - 2026-04-19

Added
- 基本機能・サブパッケージを初期実装
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用するよう切り替え。
    - BrokerClientFactory を利用して実行時にブローカークライアント（実ブローカ or モック）を生成。
    - エンジンは別スレッドで実行し、data/stop_requested.flag により外部からの停止要求を検知して安全に停止できる。
    - 起動時にプロセス優先度を "high" に設定するフローを組み込んでいる。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録する設計。
    - stop_requested.flag 検知でループを終了。
- 設定/環境管理
  - config.py
    - Settings クラスで環境変数をラップして提供。
    - 自動的にプロジェクトルート（.git 或いは pyproject.toml）を探索して .env / .env.local を読み込む仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
    - .env の読み込みロジックはクォートやエスケープ、コメント処理に対応。
    - 多数のプロパティを提供（J-Quants / kabu API / DB パス / paper trading 設定 / 監視閾値 等）。
  - config_setup.py
    - .env 作成・更新の対話式ウィザード。
    - 既存 .env の読み込み、入力補助、保存機能を備える。
  - validate_config.py
    - 起動前検証 CLI。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml 存在・パース等を検査。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30 日保持）をルートロガーに設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR の環境変数に対応、既存ハンドラのクリア処理あり。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ。
    - set_process_priority(level) で high/normal/low を設定。set_cpu_affinity(cpu_count) で最初の N コアにピン留め可能（権限や OS により失敗する場合は警告でフォールバック）。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、同点は signal_rank）および候補選定関数 select_candidates。
    - 等比率・スコア重み（calc_equal_weights / calc_score_weights）。全スコアが 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別エクスポージャの計算に基づき、指定上限を超えるセクターの新規候補を除外）。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップし、未知のレジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing の実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap の考慮、コストバッファ（手数料・スリッページ）の反映、スケーリングと端数処理（残余キャッシュでの追加配分ロジック）を備える。
- 研究用モジュール
  - research/factor_research.py（ファクター計算基盤）
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いたモメンタム / ボラティリティ / バリュー 等のファクター計算設計（関数群の一部実装）。
- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）。
    - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を集計し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）で PASS/FAIL 判定を出力。
    - P95 計算や日付フィルタ、DB 存在チェックに対応。
- DB 初期化 / 監視テーブル
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルが存在することを保証する処理を複数スクリプトで呼び出す（冪等）。

Changed
- N/A（初回リリースのため、変更履歴は追加のみ）

Fixed
- N/A（初回リリースのため、修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Known limitations / TODO（コードコメントより推測）
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性があり将来のフォールバック価格導入が検討されている。
- position_sizing: 将来的に銘柄別の lot_size を持たせる設計への拡張予定（現状は全銘柄共通 lot_size）。
- research/factor_research.py はファクター計算の骨組みを持つが、実運用に向けた追加実装が残されている可能性あり（ファイル終端が途中で途切れているため）。
- デフォルトの監視用 SQLite は環境にかかわらず本番 sqlite_path を用いる設計のため、テスト実行時に注意が必要。
- 一部の機能（プロセス優先度設定や CPU affinity）は実行環境の権限や OS に依存し、失敗した場合は警告扱いでスキップされる。

参考: 主な環境変数・デフォルト値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）

以上がコードベースから推測した初回リリース（0.1.0）の変更履歴です。必要であれば、各ファイルごとの詳しい変更点やリリースノートの言い回しを調整します。
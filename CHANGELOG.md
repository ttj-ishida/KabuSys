Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
-----

- 初回リリース（ベース機能群を実装）。
- 実行用・監視用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンをデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）を検知して安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化を実行）。
- 設定管理モジュール（config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 高機能な .env パーサー実装（コメント・export 形式・クォートとエスケープに対応）。
  - 環境変数アクセス用 Settings クラスを提供（J-Quants / kabuAPI / LINE / DB / 監視 / システム設定等）。
  - 設定の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder.py
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重(calc_score_weights)。
  - risk_adjustment.py
    - セクター集中制限(apply_sector_cap)、市場レジームに応じた乗数(calc_regime_multiplier)。
    - 未知のレジームは警告してフォールバックする挙動。
  - position_sizing.py
    - position size（株数）計算ロジック（risk_based / equal / score）。
    - aggregate cap のスケーリングと lot_size（単元株）での丸め処理。
    - cost_buffer による保守的見積り対応。
- リサーチ機能（kabusys.research）
  - factor_research.py
    - Momentum / Volatility / Value のファクター計算（DuckDB を用いた SQL ベース実装）。
  - feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計サマリ(factor_summary)、ランク化(rank)。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの実装（バッチ送信、トークン肥大化対策、リトライ・バックオフ、レスポンス検証、スコアクリップ、部分失敗を考慮した DB 更新手順など）。
  - ニュース収集ウィンドウ計算（JST ベースの明確な定義）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - CLI オプションで期間指定（--from / --to）や DB パス指定（--db）が可能。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティ。
    - 権限不足や未対応 OS では警告してスキップする安全設計。
  - DuckDB / SQLite を併用する設計。監視用には sqlite、分析用に duckdb を利用。

Changed
-------

- なし（初回リリース）

Fixed
-----

- なし（初回リリース）

Deprecated
----------

- なし

Removed
-------

- なし

Security
--------

- API キーやトークンは環境変数での提供を期待する（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。README/.env.example に従い安全に管理してください。
- .env の自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数が利用可能（テスト時などに推奨）。

Notes / Migration
-----------------

- 環境変数の主な設定項目
  - KABUSYS_ENV: development / paper_trading / live（必須。無効値は例外）
  - PAPER_FILL_MODE: instant / partial / never / reject（paper_trading 用）
  - PAPER_TRADING_SQLITE_PATH: paper trading DB（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。1 未満や非整数は無効と見なされデフォルトにフォールバック）
  - OPENAI_API_KEY: news_nlp の OpenAI API キー
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限がない場合は警告が出ますが処理は継続します。
- run_execution は停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用します。既に停止フラグがある場合は起動を中止します。
- paper_verification_report は DuckDB を使わず SQLite の paper_trading DB を読み、運用上の健全性指標を算出します。DB が存在しない場合はエラー表示して終了します。
- position_sizing の将来の拡張点:
  - 銘柄別 lot_size マップの導入を想定した TODO コメントあり。
  - apply_sector_cap で price が欠損した場合の取り扱いに注意（現状は 0.0 を用いるため過少見積りとなる可能性がある旨の注記あり）。
- news_nlp は堅牢性（バックオフ、レスポンス検証、部分更新）を考慮して実装されていますが、OpenAI API の利用にはキーと利用料が必要です。

Known issues
------------

- ai/news_nlp.py は大枠の実装を含むものの、外部 API の全例外網羅や運用時のメトリクス収集は今後の作業項目です。
- 一部の TODO コメントにある改善（価格フォールバックや銘柄別単元対応など）は未実装です。
- DuckDB executemany の制約（空パラメータの扱い）に注意して実装されていますが、運用での大規模データ投入・並行処理には追加検証が必要です。

Authors
-------

- 初期実装: KabuSys チーム（コード中の設計コメントに基づく）

License
-------

- リポジトリ内の別記が無い場合は適宜プロジェクト方針に従ってください。
Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

注: 以下の変更項目は、与えられたコードベースの内容から推測して作成しています。

Unreleased
---------

- 追加
  - 研究モジュールの拡張予定
    - research/factor_research.py にファクター計算の骨組み（Momentum / Value / Volatility / Liquidity）を実装中。DuckDB を利用した prices_daily/raw_financials ベースの計算を想定。現状モメンタム計算の実装が途中。

- 修正 / 改善予定
  - 各種ロギング・エラーハンドリング強化や、position sizing の lot_size 銘柄別対応などの拡張がコメントとして残されている（将来対応予定）。

0.1.0 - 2026-04-19
-----------------

初回リリース — 基本的な自動売買フレームワークとユーティリティ群を追加。

- 追加
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 起動時にプロセス優先度を "high" に設定。停止は data/stop_requested.flag により行う。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
      - スレッドでエンジンを実行し、停止フラグ検知で安全に停止。PID ファイルを書き込む仕組み。

  - 設定 / CLI
    - config.py
      - .env ファイルの自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env のパースは export プレフィックス、クォート、エスケープ、行内コメント（スペース直前の #）等に対応。
      - Settings クラスを提供。J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定プロパティ（is_live/is_paper/is_dev）等を取得するユーティリティを実装。
      - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の入力検証を実装。
      - 自動ロード無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - config_setup.py
      - .env の初期作成・対話式更新ウィザードを追加。必須項目のマスク表示、選択肢サポート、.env の読み書き（テンプレート）を実装。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数のチェック、プレースホルダ警告、DB パスや config/*.yaml の存在確認、KABUSYS_ENV=live 向けの追加ガードを実装。--strict オプションで警告もエラー扱いにできる。

  - ポートフォリオ構築ロジック（純粋関数群）
    - portfolio/portfolio_builder.py
      - 銘柄候補選定（スコア降順、タイブレークルール）および等配分・スコア加重配分の計算関数を追加。スコア総和が 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中上限を適用する apply_sector_cap を追加（当日売却予定コードの除外、"unknown" セクターは緩和）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップ、未知はフォールバック）。
    - portfolio/position_sizing.py
      - ポジションサイズ計算 calc_position_sizes を追加。allocation_method として "risk_based" / "equal" / "score" をサポート。
      - 損切り率、risk_pct、max_position_pct、max_utilization、単元（lot_size）、コストバッファを考慮した計算、aggregate cap によるスケーリングと端数調整のロジックを実装。

  - ユーティリティ
    - utils/logging_setup.py
      - 統一ロギング設定ユーティリティを追加。コンソール(stdout) と 日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決ルール、既存ハンドラのクリア、ファイル出力失敗時のフォールバックを実装。
    - utils/process_priority.py
      - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。psutil を利用し、権限不足や未対応 OS では安全にスキップして警告を出す。

  - モニタリング DB 初期化
    - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等的に初期化）。

  - Execution 周りの依存コンポーネント組み立て
    - execution パッケージ（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）の組み立てと既定の RiskConfig を run_execution.py で設定。

  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99% 等）に基づき PASS/FAIL を出力。DB パスは環境変数またはコマンドラインで指定可能。

- 変更（設計上の挙動）
  - 監視プロセスは監視 DB（sqlite）に常に本番 sqlite_path を使用する（環境による分離が不要な設計判断）。
  - run_execution は paper_trading 環境時に DB を分離（paper_sqlite_path）することで、本番データと完全に分離される設計。

- 修正 / 安全策
  - 環境変数パースと検証を強化（クォートやエスケープの取り扱い、プレースホルダ検出、無効値でのフォールバック通知）。
  - ポーリング間隔の環境変数 MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告し、デフォルト値にフォールバックするガードを追加。
  - プロセス優先度や CPU affinity の設定失敗時に例外を吐かず警告のみ出すことで起動の堅牢性を向上。

- 既知の制限 / TODO
  - research/factor_research.py の実装が未完（モメンタム関数実装途中）。Value/Volatility/Liquidity の実装と統合テストを予定。
  - position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map での拡張を想定）。
  - apply_sector_cap の価格欠損時の取り扱いは要改善（現在は 0.0 を使用すると過少評価のリスクあり）。
  - 一部のファイル I/O（ログディレクトリ作成、.env 読み書き）で権限や環境依存の失敗が想定されるため、運用時に注意。

注記
----
- バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。  
- 日付はコード提供日を基に設定しています（推定）。  
- 実際の変更履歴はコミット履歴やリリースノートに基づいて確定してください。
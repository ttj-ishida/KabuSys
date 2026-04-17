CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットで記載しています。
日付は本コードスナップショットの作成日（2026-04-17）を使用しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本アプリケーション骨格を実装。
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として登録。
- 実行エントリ / サービス
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。デーモンスレッドでセッション実行、data/stop_requested.flag による安全停止、実行 PID 書き込み（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をコード内で定義。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。  
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0 以下の値は無効扱いでデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明確化。
    - 起動直後にプロセス優先度を "high" に設定（utils.process_priority の set_process_priority を利用）。
- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。  
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env のパース実装（export 句、クォート内エスケープ、インラインコメントの扱い等）。
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB / 監視設定 / system settings）。
    - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）。
    - KABUSYS_ENV / LOG_LEVEL の有効値検査。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定（score 降順 + signal_rank tie-break）、等金額配分、スコア重み配分（スコア全て 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは警告のうえ 1.0 をフォールバック）。
  - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）。  
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate キャップ、スケーリングと残差配分アルゴリズムを実装。
    - 価格欠損時のスキップやログ出力あり。
- 監視・ツール
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルが存在することを保証（冪等）。
  - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を出力。  
    - CLI オプション --from/--to/--db をサポート。P95 計算、日付フィルタ生成、DB 存在チェックやエラー耐性を実装。
- 研究 / ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算（momentum, volatility, value）。  
    - MOMENTUM (1M/3M/6M, MA200 dev)、ATR/atr_pct、20日平均売買代金/出来高変化率、PER/ROE の計算を実装。データ不足時は None を返す。
  - research.feature_exploration: 将来リターンの計算（任意ホライズン）、IC（スピアマンρ）計算、ランク付け、ファクター統計サマリーを追加。外部依存を使わず標準ライブラリで実装。
  - research.__init__: 必要な関数群を公開（zscore_normalize は data.stats からインポート）。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント分析して ai_scores に書き込む処理を追加。  
    - ニュース収集ウィンドウ計算（JST ベースで UTC に変換）を実装。記事集約、バッチ（最大 20 銘柄）送信、JSON Mode レスポンスバリデーション、スコア ±1.0 クリップ、部分成功の扱い（削除→挿入の差分更新）等の設計を導入。  
    - リトライ（429/ネットワーク/5xx）に対する指数バックオフ実装方針。API キー未設定時は ValueError を送出。
- ユーティリティ
  - utils.process_priority: psutil を使ったプロセス優先度設定ユーティリティを追加（Windows / POSIX 差分吸収、AccessDenied 等は警告でスキップ）。CPU affinity 設定関数 set_cpu_affinity を追加。
- パッケージ初期化
  - package の __all__ を整備（portfolio, research などを公開）。

Changed
- 設定まわりの振る舞いを明確化。
  - .env ロード時、OS 環境変数を保護する protected 処理を追加。`.env.local` は `.env` の上書きとして扱う。
- monitoring と execution の DB 接続ポリシー
  - run_monitoring は常に本番用 sqlite_path を用いる旨を明確化（モニタは環境に依存しない）。run_execution は paper_trading 環境では専用 DB を使用する。

Fixed
- 多くの関数でデータ不足時の None ハンドリングや sqlite/duckdb における OperationalError を受けた場合のフェイルセーフ処理を追加（tools.paper_verification_report 等で例示）。
- 環境変数パースの堅牢化（引用符、エスケープ、コメント処理の改善）。

Security
- OpenAI API キーや各種秘密情報は環境変数から取得する設計。自動 .env ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。OS 環境変数は .env で上書きされないよう保護。

Notes / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須 (未設定時は ValueError)。
  - OpenAI を利用する場合は OPENAI_API_KEY を設定する必要がある（ai.news_nlp を呼ぶとき）。
- 環境変数による挙動制御
  - MONITOR_POLL_INTERVAL: 監視のポーリング秒数を指定（正の整数、デフォルト 60）。
  - PAPER_FILL_MODE: paper_trading の MockBroker 挙動。値は "instant" | "partial" | "never" | "reject"。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB のパスを上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用途）。
- 停止制御
  - data/stop_requested.flag を作成することで監視/実行プロセスを安全に停止可能。実行 PID は data/execution.pid に書き込まれる想定。
- 実装上の既知の制約 / TODO
  - position_sizing の価格欠損時のフォールバック（前日終値など）は未実装（TODO コメントあり）。
  - 単元株 lot_size は現在グローバル固定（将来的に銘柄別拡張を想定）。
  - ai.news_nlp の処理は設計途中（スニペット末尾が途中で切れているため、実運用前に完全実装の確認が必要）。

お問い合わせ
- 変更内容や移行に関して不明点があれば、開発チームのドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照するか、実装担当までお問い合わせください。
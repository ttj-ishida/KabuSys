CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点で未リリースの変更はありません。）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース。KabuSys の基本コンポーネントを追加。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時に mock ブローカーを使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）。停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
    - Execution エンジン周辺のコンポーネント（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler）の組み立て処理を実装。
    - RiskConfig によるリスク制約の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知による安全なシャットダウン、例外ハンドリング、プロセス優先度設定を実装。
    - 監視用 DB 初期化 (init_monitoring_db) と DuckDB 連携をサポート。
  - 設定管理
    - config.py: .env/.env.local の自動読み込み（プロジェクトルート検出）と詳細なパースロジックを実装。export 形式やクォート、インラインコメントの認識、OS 環境変数保護（上書き制御）に対応。
    - Settings クラス: 各種環境変数に対するプロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別判定など）を実装。妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を含む。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順 + tie-break）と重み計算（等配分・スコア加重）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市況レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 複数方式（risk_based / equal / score）に対応した発注株数計算、単元株丸め、aggregate cap によるスケールダウン処理、コストバッファ対応を実装。
    - portfolio パッケージとしてエクスポート設定を追加。
  - リサーチ（ファクター・解析）
    - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装（DuckDB の prices_daily/raw_financials テーブル参照）。
    - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部依存を使わず標準ライブラリで実装。
    - research パッケージのエクスポート（zscore_normalize などを含む）。
  - AI ニューススコアリング
    - ai/news_nlp.py: raw_news と news_symbols から銘柄ごとにテキストを集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを -1.0〜1.0 でスコア付けする処理を実装。バッチ処理、トークン肥大化対策（記事数・文字数制限）、リトライ（指数バックオフ）、レスポンス検証、スコアのクリップ、部分書き換え（部分失敗時に既存スコアを保護）等を考慮した設計。
    - ニュース収集ウィンドウ計算（JST→UTC 変換）ユーティリティを実装。
  - ユーティリティ
    - utils/process_priority.py: Windows / POSIX 間の差を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 固定（set_cpu_affinity）。psutil を用いて権限不足や未対応環境では警告を出して安全にスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。システム稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を集計し PASS/FAIL 判定を出力。閾値（稼働率 99%、成立率 90% 等）をドキュメント化。
  - パッケージ基礎
    - __init__.py にバージョン情報 __version__="0.1.0" を追加。

Changed
- .env の自動読み込みの振る舞いを明確化:
  - 読み込み順序: OS 環境 > .env.local > .env。OS 環境変数は protected として上書きを禁止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動読み込みを無効化可能。
- run_monitoring/run_execution 実行時に最初にプロセス優先度を設定するよう統一。

Fixed
- .env パースの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォート無し時のインラインコメント判定などを改善し、実運用での .env 記載バリエーションに対応。
- position_sizing の合計投下額が利用可能現金を超えた場合のスケールダウン処理で、端数（lot 単位）を安定して配分するアルゴリズムを実装。

Security
- 環境変数による機密情報（API キー等）取得の扱いを明確化（Settings・score_news の引数/環境変数参照）。API キーが未設定の場合に明示的なエラーを出すようにした。

Notes
- Paper Trading と本番データベースは明確に分離される設計です。paper_trading モードでは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、実行ログ・トレードログ等を本番と混在させません。
- DuckDB は主に市場データ / ファクター計算用に使用され、SQLite は実行・監視ログ等の永続化に使用します。
- ai/news_nlp.py の実装は API 呼び出しの堅牢化（リトライ・レスポンス検証）を重視しています。API 使用量やレスポンス形式に依存するため、運用時は OPENAI_API_KEY の管理、モデル変更、レート制限設定に注意してください。

Contributing
- バグ修正・機能追加は issue/PR を歓迎します。コードはドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に基づいて実装されています。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
日付はリポジトリの現行バージョン（__version__ = "0.1.0"）のリリース日として 2026-04-17 を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys のコア機能を追加。
  - 実行系 / 監視系ランチャー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用（settings.is_paper 判定）。
      - 停止フラグファイル (data/stop_requested.flag) の検出による安全な停止、実行用 PID ファイル管理、スレッドでの Engine 実行とタイムアウト付き join を実装。
      - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager の組み立て。
      - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ検出、例外発生時のロギング、リソースクリーンアップ（DB 接続クローズ）を実装。
  - 設定管理
    - config.py: Settings クラスと自動 .env 読み込み機能を追加。
      - プロジェクトルート検出（.git / pyproject.toml）に基づく .env / .env.local 自動読み込み（OS 環境変数を保護）。
      - .env パースの強化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
      - 必須環境変数チェック（_require）や各種プロパティ（DB パス、PID/kill flag パス、しきい値、PAPER_FILL_MODE 検証、KABUSYS_ENV / LOG_LEVEL 検証など）を提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）の実装。単元株丸め、per-position と aggregate の上限、cost_buffer による保守的見積り、スケールダウン時の端数配分ロジックを含む。
    - これらをまとめて kabusys.portfolio パッケージとして公開。
  - リサーチ・ファクター計算
    - research/factor_research.py: momentum、volatility、value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB の prices_daily / raw_financials テーブルを前提に SQL で計算。
    - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計（factor_summary）、rank ユーティリティを実装。外部依存を避け標準ライブラリのみで実装。
    - research/__init__.py で主要 API をエクスポート。
  - AI ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む基本設計を追加。
      - ニュース収集ウィンドウ算出（JST ベース → UTC 変換）、銘柄ごとの記事集約、1 銘柄あたりトリム制限（記事数・文字数）、バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフとリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 書換保護（コード絞り込み）などの設計方針を実装済み。
      - API キー未設定時は ValueError を送出する安全チェックを実装。
  - ユーティリティ
    - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定・CPU affinity ユーティリティを追加（set_process_priority, set_cpu_affinity）。
      - Windows/Linux/macOS 等を考慮し、権限不足や未サポート環境では警告してスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して標準出力に整形して出力。
      - デフォルト DB パスは data/paper_trading.db。コマンドライン引数 --from/--to/--db をサポート。
      - 閾値（uptime 99%、fill_rate 90%、send_rate 95%、P95 200ms）に基づく PASS/FAIL 判定を実装。

Changed
- なし（初回リリースのため新規追加が中心）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数に依存する機密情報（OpenAI API キー、J-Quants トークン、Kabu API パスワード等）は Settings を通じて必須チェックを実施。未設定時は明示的な例外を発生させる設計。

Notes / Design highlights
- paper_trading と本番 DB の明確な分離: run_execution は paper_trading 環境で専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB を汚さない設計。
- run_monitoring は運用監視のために「環境にかかわらず本番 sqlite_path を使う」という挙動を採用（意図的な設計）。
- .env パースはシェル風の export プレフィックスとクォート内エスケープに対応し、既存 OS 環境変数を保護する読み込み優先順を採用。
- リサーチ・ファクター・ポートフォリオ計算等は副作用なしの純粋関数として実装されており、ユニットテストや再利用が容易な設計になっている。

今後の候補（実装予定・検討）
- ai/news_nlp の API 呼出し部分の完全実装（ファイル末尾が途中で切れているため、現在は設計・一部実装）。
- 銘柄ごとの lot_size を stocks マスタで管理する拡張（position_sizing の TODO）。
- 監視・実行のより詳細なメトリクス収集・アラート機能強化。
- DuckDB の INSERT/DELETE 実行時のトランザクション関連の堅牢化（部分失敗時のロールバック戦略）。

---
この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリポジトリの意図に基づいて適宜調整してください。
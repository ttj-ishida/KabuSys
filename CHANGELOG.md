KEEP A CHANGELOG
全ての変更は Keep a Changelog の形式に従って記載しています。  
セマンティック バージョニングを採用しています: https://semver.org/

Unreleased
---------
Added
- 監視プロセス起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を設定し、監視用 DB（SQLite）と分析用 DuckDB を開いてループで monitor.check_once() を実行する。監視テーブル初期化処理を実行。
- 実行エンジン起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient を利用できる設計。起動時にプロセス優先度を設定し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行する。
- 設定管理を強化
  - config.py: .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込む）。.env パーサーは export プレフィックス、クォート文字列、エスケープ、インラインコメントを適切に処理。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。各種設定項目（DB パス、PID / kill flag パス、閾値、環境判定フラグ等）を Settings クラスで提供。
- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等分配・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算を実装。単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer の考慮、端数配分ロジック等を網羅。
  - portfolio.risk_adjustment: セクター集中上限を適用して候補を除外する apply_sector_cap、レジームごとの投下資金乗数 calc_regime_multiplier を実装。
- 研究（Research）モジュールを追加
  - research.factor_research: DuckDB を用いるファクター計算 (calc_momentum, calc_volatility, calc_value)。モメンタム（1M/3M/6M、MA200乖離）、ATRベースのボラティリティ、財務指標（PER/ROE）を計算。データ不足を考慮した NULL ハンドリング。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク付けユーティリティ (rank) を実装。外部ライブラリに依存せず標準ライブラリで実装。
- AI ニュース NLP スコアリング機能を追加
  - ai.news_nlp: raw_news / news_symbols を集計して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む機能を実装。バッチ送信（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフによるリトライ、API キー解決ロジック、出力バリデーション、スコアのクリップ（±1.0）などを備える。ニュースの時間窓計算（JST→UTC 変換）を提供。
- ツール: Paper Trading 検証レポート
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して CLI レポートを出力するスクリプトを追加。期間フィルタ（--from / --to）対応、各種閾値に基づく PASS/FAIL 判定を行う。
- ユーティリティを追加
  - utils.process_priority: プラットフォーム差を吸収してカレントプロセスの優先度設定（Windows / POSIX）と CPU affinity 設定を提供。権限不足等のケースで安全にフォールバックするハンドリングを実装。
- パッケージ初期化
  - __init__.py: パッケージのバージョン（0.1.0）および主要サブパッケージのエクスポートを定義。

Changed
- なし（初期リリース相当）

Fixed
- なし（初期リリース相当）

[0.1.0] - 2026-04-12
-------------------
Added
- 初期公開リリース。上記の各機能をまとめてリリース:
  - 実行・監視の起動スクリプト（run_execution, run_monitoring）
  - 環境設定・.env 自動読み込みと堅牢なパーサー（config.Settings）
  - ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ算出・リスク調整
  - 研究用ファクター計算 / 特徴量解析（DuckDB ベース）
  - AI ニュースセンチメントスコアリング（OpenAI 統合）
  - Paper Trading の検証レポート CLI
  - プロセス優先度 / CPU affinity ユーティリティ
  - DuckDB と SQLite を併用するデータアクセス設計
  - PID / kill flag 等の運用用設定

Security
- なし

Notes / 補足
- 設定周りは OS 環境変数を優先し、.env/.env.local の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB から分離された専用 SQLite（デフォルト data/paper_trading.db）を使用します。
- ai.news_nlp は OpenAI API キーが必須です（api_key 引数または OPENAI_API_KEY 環境変数）。

今後の予定（参考）
- 銘柄別の lot_size をマスタ化して position sizing に反映する拡張
- price の欠損時のフォールバック価格ロジック（前日終値や取得原価）
- ai.news_nlp の部分失敗時のトランザクション性向上（部分コミットの取り扱い改善）
- テストカバレッジ強化および DuckDB SQL の最適化

--- End of CHANGELOG ---
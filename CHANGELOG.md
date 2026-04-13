Keep a Changelog
=================

全ての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

- (なし)

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初期リリース。自動売買システムのコア機能群を実装。
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定する処理を組み込み。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使って本番 DB と完全分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を起動。  

- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動ロードを行う（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env と .env.local の読み込み順と上書きルール（OS 環境変数は保護）。
    - .env 1行パーサーの実装（export プレフィックス、クォート、エスケープ、インラインコメントの扱いに対応）。
    - 必須環境変数取得ユーティリティ _require と各種設定プロパティ（DB パス、PID ファイル、しきい値、環境判定など）。
    - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 監視・ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）設定を実装（Windows / POSIX を吸収）。
    - CPU affinity を最初 N コアに固定するヘルパーを実装。
    - アクセス権限や未対応 API を想定したフォールバックとログ出力を実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有を基に新規候補を除外するロジック）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告のうえフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数決定ロジック。
    - リスクベース計算、1銘柄上限、lot_size（単元）丸め、aggregate cap によるスケールダウン、余剰キャッシュに対する端数処理（再配分）を実装。
    - cost_buffer による手数料/スリッページの保守的見積もり対応。

- 研究（Research）
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いて各種ファクター（モメンタム、ATR 等、PER/ROE）を計算。
    - 200日移動平均や ATR の窓サイズに基づいた不足データ時の None ハンドリング。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）をまとめて取得するクエリ実装。
    - calc_ic: スピアマンランク相関（IC）算出。データ不足や ties（同順位）に対する安定処理を実装。
    - factor_summary / rank: ファクターの基本統計量算出とランク変換ユーティリティ。
  - research.__init__ で主要関数と zscore_normalize を公開。

- AI / ニュースNLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores へ書き込むワークフローを実装。
    - タイムウィンドウ計算（JSTベース → UTC に変換）と記事集約、1銘柄あたりの文字数/記事数制限を実装。
    - 最大バッチサイズ、JSON Mode 出力期待、スコアの ±1.0 クリップ、チャンク単位 API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ実装方針を反映。
    - API キー解決（引数優先、環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError。
    - フェイルセーフ設計: API 失敗時はスキップして継続、部分失敗時に既存スコアを保護するための限定 DELETE/INSERT 戦略（実装方針として記載）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポートジェネレータを追加。
    - CLI オプション (--from, --to, --db) を提供。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - P95 計算ユーティリティ、しきい値による PASS/FAIL 判定、整形出力を実装。
    - DB 存在チェックやテーブル未存在時の耐性（OperationalError を捕捉して N/A 扱い）を実装。

Changed
- (初期リリースのため履歴なし)

Fixed
- (初期リリースのため履歴なし)

Deprecated
- (該当なし)

Removed
- (該当なし)

Security
- (該当なし)

Notes / 想定運用上の注意
- 設定値やしきい値（CPU/MEM/DISK/各種ポートフォリオパラメータ）は環境変数で上書き可能。運用時は .env/.env.local の管理に注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存で権限不足により失敗する場合があり、その際は WARN ログを出してスキップします。
- Paper Trading と本番 DB は分離される設計だが、運用時はパス設定（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を必ず確認してください。
- OpenAI を使う機能は API キーと利用制限に依存するため、レート制限や料金・プライバシーの観点で運用ルールを設けてください。
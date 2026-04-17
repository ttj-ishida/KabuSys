CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/),
およびセマンティックバージョニングに準拠しています。

Unreleased
----------

Added
- news_nlp: OpenAI を利用したニュースの NLP スコアリング機能を実装中。  
  - ニュース集約、バッチ送信、リトライ、レスポンス検証、スコアのクリップ等の設計を導入。
  - タイムウィンドウ算出関数 calc_news_window を提供。
- 各種ドキュメント・設計注釈をソース内に追加（PortfolioConstruction.md / StrategyModel.md 等への参照）。

Changed
- process_priority: 優先度設定・CPU affinity のユーティリティを強化し、Windows／POSIX の差分を吸収。権限不足などの例外時には警告を出して安全に継続するよう改善。

Fixed
- .env パーサーを堅牢化:
  - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理、空白トリム等に対応。
  - .env ロード順（OS 環境変数 ＞ .env.local ＞ .env）と上書き保護ロジックを明確化。

Known issues / TODO
- ai/news_nlp.py が本リリース時点で途中実装（ファイル末尾が不完全に切れている）になっています。完全な動作には追加実装が必要です（未処理分あり）。
- portfolio.position_sizing: 価格欠損時のフォールバック（前日終値や取得原価）について TODO コメントあり。将来的な改善予定。
- 将来的に lot_size を銘柄単位で管理する拡張を想定したコード注釈あり。

v0.1.0 - 2026-04-17
-------------------

Added
- 初回リリース（0.1.0）として以下の主要機能を追加：
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db 想定）を使用し、本番 DB と分離。
      - BrokerClientFactory を使ってブローカークライアントを生成（paper_trading 時は MockBrokerClient を利用する想定）。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。停止フラグ（data/stop_requested.flag）検知で安全に停止。
      - Execution 用 PID ファイル管理（data/execution.pid）をサポート。
      - RiskManager にデフォルト値付きの RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視系
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告）。
      - 監視は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用して監視テーブルを初期化。
      - 停止フラグ（data/stop_requested.flag）とプロセス優先度設定に対応。
  - 設定管理
    - config.py: 環境変数読み込み/管理モジュールを追加。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env / .env.local 自動読み込み（無効化フラグあり）。
      - export プレフィックス、クォート、インラインコメント等に対応するパーサを実装。
      - 必須キー取得ヘルパー _require、各種設定プロパティ（DB パス、API トークン、閾値など）を提供。
      - 入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
      - calc_score_weights は全スコアが 0 の場合に等重配分へフォールバックして警告。
    - portfolio.risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
      - セクター上限超過時は同セクターの新規候補を除外。unknown セクターは上限適用外。
      - レジーム乗数は bull/neutral/bear にマッピングし、未知はフォールバック。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）。
      - 単元株丸め（lot_size）、1銘柄上限・aggregate cap（available_cash）でのスケーリング、残差処理ロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
  - リサーチ／ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（DuckDB 経由で prices_daily / raw_financials を参照）。
      - mom_1m/3m/6m、MA200 乖離、ATR20、相対 ATR、20日平均売買代金、volume ratio、PER/ROE 等を計算。データ不足時は None を返す。
    - research.feature_exploration: 将来リターン計算（複数ホライズン）・IC（Spearman の ρ）・統計サマリー（count/mean/std/min/max/median）等を実装。外部ライブラリに依存せず標準ライブラリで実装。
  - AI / NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント化するためのモジュール骨格を追加。
      - バッチ処理、最大記事/文字数トリム、リトライポリシー、レスポンス検証、結果を ai_scores テーブルへ置換する方針を実装。
      - OPENAI_API_KEY 未設定時は ValueError を送出する安全策を導入。
      - （注）このモジュールの一部はまだ実装途中で、完全動作には追加実装が必要。
  - ユーティリティ
    - utils.process_priority: プロセス優先度設定（Windows/Posix 対応）と CPU affinity 設定関数を実装。権限不足や未対応 OS は警告でスキップ。
  - CLI ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算して標準出力にレポート出力。閾値に基づく PASS/FAIL 判定を実施。
      - --from / --to / --db オプションで期間・DB を指定可能。
  - パッケージ初期化
    - __init__.py に __version__ = "0.1.0" を設定、主要サブパッケージを __all__ で列挙。

Changed
- 既存の起動スクリプト・エンジン設計に沿って DB 初期化（init_monitoring_db）の呼び出しを追加し、監視テーブルの存在を冪等に保証。

Fixed
- run_execution/run_monitoring: 起動時にプロセス優先度を最初に設定するように変更（パフォーマンス優先）。

Security
- API キー等の必須設定が無い場合に早期に ValueError を送出する箇所を追加（OpenAI, J-Quants, Kabu API のトークン等）。これによりキー漏れによる不整合処理を防止。

Removed
- なし（初回リリース）。

Notes / Implementation details
- DB 関連:
  - duckdb_path と sqlite_path（および PAPER_TRADING_SQLITE_PATH）を Settings 経由で取得。paper_trading モードは専用 SQLite を使用して本番データと分離する設計。
- 設計上の考慮:
  - データ取得・計算の多くは DuckDB の SQL ウィンドウ関数を活用しており、計算は DB 側で行う方針（外部 API への依存を最小化）。
  - CLI / スクリプトは停止フラグファイル（data/stop_requested.flag）を用いた外部制御に対応。
  - 例外処理や入力検証を多めに入れてフェイルセーフを重視。

Contributing
- バグ修正、ドキュメント追加、AI モジュールの完成実装など歓迎します。プルリクエストの際はテスト（ユニット / 結合）を付けてください。

-- end --
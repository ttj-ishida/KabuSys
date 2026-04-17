CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" の形式および
Semantic Versioning を意識して管理します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初版リリース。
- 基本アーキテクチャ・起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。実行停止はプロジェクト配下 data/stop_requested.flag により制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に分離して MockBroker を利用。実行停止フラグと PID ファイルに対応。
- 設定・環境変数管理
  - config.py: Settings クラスを導入。.env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）、.env パーサ（引用・エスケープ・コメント処理対応）、各種環境変数のデフォルトと検証ロジックを実装（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL 等）。
- 実行系コンポーネント（参照）
  - ExecutionEngine 周りの組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, EngineConfig 等）を起動スクリプトから利用可能に。RiskManager にはデフォルトの RiskConfig が設定され、初期ポートフォリオ値はブローカーの get_available_cash() を使用。
- 監視・データベース
  - monitoring_db.init_monitoring_db 呼び出しを通じて監視用テーブルの初期化を保証（冪等）。
  - DuckDB と SQLite の二重接続対応（分析用 / 監視用）。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes)。risk_based / equal / score 各方式、単元丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
- リサーチ／ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、ランク変換ユーティリティ。標準ライブラリのみで実装（pandas 等に依存しない設計）。
  - research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から提供）。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析して ai_scores に書き込むバッチ処理を実装。タイムウィンドウ計算、銘柄単位の集約（記事数・文字数上限）、バッチサイズ制御、リトライ（429/ネットワーク/5xx）、レスポンス検証、±1.0 でのクリップ、部分更新（既存スコア保護）の方針を採用。
- ツール群
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。日付フィルタ、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等の算出および PASS/FAIL 判定を実装。閾値（稼働率 99%、注文成功率 90% など）を定義。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）を抽象化し、権限や未対応 OS に対しては警告でフォールバック。
- パッケージ情報
  - __init__.py にてパッケージ名・バージョンを定義（__version__ = "0.1.0"）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で供給する仕様（未設定時は ValueError）。機密情報の取り扱いは .env 等で環境変数として管理することを想定。

Notes / Known limitations / TODO
- portfolio/position_sizing.calc_position_sizes:
  - lot_size は現在グローバル固定（デフォルト 100）。将来的に銘柄別 lot_size を導入する旨の TODO コメントあり。
  - price が欠損（0.0）の場合にエクスポージャー過少見積りとなる可能性がある点をコメントで記載。
- .env パーサは複雑な引用・エスケープ・コメント処理を実装しているが、極端なケースでは互換性確認が必要。
- DuckDB 側で executemany の引数が空だと制約がある旨がコメントで記載されている（ai/news_nlp のバルク置換処理等で注意）。
- run_monitoring は監視用 DB に本番 sqlite_path を使用する（KABUSYS_ENV にかかわらず）。これは監視が本番データへアクセスする設計意図。
- 設計ドキュメント参照:
  - PortfolioConstruction.md / StrategyModel.md 等の仕様に準拠した実装が多数（リポジトリ内ドキュメント参照）。

Contact / Contributing
- バグ報告・機能要望は Issue を通じてお願いします。プルリクエストでは単体テストと簡潔な説明を同梱してください。
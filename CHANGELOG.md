CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

- なし（最新の安定変更は v0.1.0 に含まれます）

v0.1.0 — 2026-04-13
-------------------

Added
- パッケージ初版リリース（__version__ = 0.1.0）。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用して MockBrokerClient を利用可能にし、本番 DB と完全分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する。
- 設定管理:
  - config.py: .env 自動ロード機能を実装（.env, .env.local、OS 環境変数の保護対応）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサにおいて export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いを実装。
  - Settings クラスを導入し、各種環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を集約。
- モニタリング DB 初期化:
  - monitoring_db の初期化呼び出しを run_monitoring/run_execution に組み込み（冪等に監視テーブルを保証）。
- Broker・Execution コンポーネント:
  - Execution 側の組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を run_execution で結合し、セッション実行フローを確立。
  - RiskManager に対する RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合に等金額へフォールバックしログ出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム不明時のフォールバックを実装。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株丸め、per-stock 上限、aggregate キャップおよびスケーリング処理（端数処理ロジック含む）を実装。
- 研究（research）モジュール:
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して各ファクターを出力。
  - research/feature_exploration.py: 将来リターン計算、IC（スピアマン）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ __all__ を整備して外部 API を公開。
- ニュース NLP:
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む処理を実装。時刻ウィンドウ計算、記事集約（1 銘柄あたり記事・文字数のトリム）、最大 20 銘柄単位のバッチ送信、レスポンス検証、スコア ±1.0 クリップ、API リトライ（429/5xx/タイムアウト/ネットワーク断の指数バックオフ）などの堅牢化を実施。
  - calc_news_window ユーティリティを提供（JST 時刻基準の窓を UTC naive な datetime で返す）。
- ユーティリティ:
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice 値対応）。set_cpu_affinity による CPU affinity 設定機能も実装。権限不足や非対応環境に対しては警告を出して安全にスキップ。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどの指標を集計し閾値と比較して PASS/FAIL を出力するコマンドラインツールを提供。--from/--to/--db オプションをサポート。
- DB/分析:
  - DuckDB を分析用 DB（duckdb_path）として統合。research/ai 等から DuckDB 接続を受けて SQL ベースで処理。

Changed
- なし（初回リリースのため該当なし）

Fixed
- なし（初回リリースのため該当なし）

Security
- ai/news_nlp.py: OpenAI API キーが未設定の場合は明示的に ValueError を送出し、誤った無条件の API 呼び出しを防止。

Notes / Behavior details
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を環境変数で上書き可能。0 以下や不正値はデフォルト 60 秒にフォールバックし、警告ログを出す。
- .env 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は上書き保護される。
- PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE: Paper Trading 用の挙動を細かく制御する環境変数をサポート（検証済みの有効値とバリデーションを持つ）。
- Monitoring は run_monitoring 起動時に必ず本番 sqlite_path（Settings.sqlite_path）を使用する設計（環境にかかわらず本番監視データを記録）。
- ExecutionEngine を paper_trading モードで動かした場合、監視テーブルは paper DB に対しても初期化される（冪等）。DuckDB は両モードで共通して使用される。

Acknowledgements
- 本リリースは初版機能群の取りまとめです。将来的な改善点（価格フォールバック、銘柄別単元対応、より高度なリトライ戦略やメトリクスの追加など）はコード内 TODO コメントや設計ノートに記載しています。
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
変更履歴はすべて日本語で記載します。

Unreleased
---------

（現在のワークツリーに対する未リリースの変更があればここに記載します。）
例: なし

0.1.0 - 2026-04-16
-----------------

初回公開リリース。本リポジトリに含まれる主要機能および実装の概要を示します。

Added
- 実行/監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用に分離された SQLite DB (data/paper_trading.db／環境変数で上書き可) を利用する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag で検知。

- 設定管理
  - config.py: Settings クラスを追加し、環境変数から各種設定（API トークン、DB パス、閾値、環境種別など）を提供。自動で .env/.env.local を読み込み（プロジェクトルート検出ロジック有）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 環境変数パーサは export プレフィックス、クォート文字列、インラインコメントの扱い、上書きルール（protected）等に対応。

- 監視データベース初期化
  - monitoring_db 初期化を実行起動時に担保する処理を導入（冪等に監視テーブルを作成）。

- Execution コンポーネント骨組み
  - Execution 系の依存コンポーネントを組み立てるロジック（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組合せ）を run_execution で起動できるように実装。RiskConfig にデフォルト値を設定し、初期ポートフォリオ値は broker.get_available_cash() を参照。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。paper_trading の SQLite DB を読み取り、稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。期間フィルタ（--from／--to）と DB パス指定（--db）に対応。閾値はソース内定数で管理（稼働率 99%、注文成功率 90% 等）。

- ポートフォリオ構築ユーティリティ
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限の対象外にする挙動を明示。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく注文株数計算を実装。単元株（lot_size）丸め、1 銘柄上限・全体利用上限（available_cash）を考慮したスケーリング、cost_buffer による保守的コスト見積りを実装。

- 研究（Research）モジュール
  - research/factor_research.py: momentum, volatility, value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する。十分なデータがない場合は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。外部依存を持たず標準ライブラリで実装。
  - research/__init__.py で主要 API を公開（zscore_normalize を含む）。

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py: raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成して ai_scores テーブルへ書き込むロジックを追加。処理はバッチ（最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク/5xx のリトライ（指数バックオフ）、JSON 出力の厳密なバリデーションなど堅牢化を図る設計。ニュース集計ウィンドウ計算のユーティリティ（calc_news_window）を提供。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム抽象化されたプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。Windows と POSIX（Linux, Darwin, FreeBSD）を吸収し、不可能な場合は警告を出して安全にスキップする。

Changed
- ログ・例外ハンドリングの強化
  - run_monitoring/run_execution の各起動スクリプトで基本ログ設定を行い、例外発生時のログや停止フラグ検知で安全にシャットダウンするフローを整備。
  - calc_score_weights や position_sizing 等、データ不足時にフォールバックすることで呼び出し側の安全性を向上。

Fixed
- 環境変数ファイルパーサの堅牢化
  - config._parse_env_line が export プレフィックス、クォート（シェル風のバックスラッシュエスケープ）、およびインラインコメント扱いを正しく処理するように改善。これにより複雑な値を .env に書けるようになった。
  - .env 読み込み時に既存 OS 環境変数を保護する protected 引数の導入により、デプロイ環境の環境変数を誤って上書きしないようにした。

- ポジションサイズ計算の安全性向上
  - calc_position_sizes における aggregate cap スケーリングで lot_size 単位の切り詰めと残余キャッシュを使った分配を実装し、端数処理で不整合が起きにくくした。
  - price が欠損した場合のスキップや、負の/ゼロ価格に対する防御ロジックを追加。

- Research 算出の堅牢性
  - calc_momentum / calc_volatility / calc_value 等で、窓サイズ不足時に None を返す、NULL の伝播を適切に扱うなど不完全データに耐える実装にした。
  - feature_exploration.rank は浮動小数の丸め誤差対策（round(..., 12)）を導入し、同順位（ties）処理を安定化。

Notes / Implementation Details
- DB: 実行系は sqlite3（軽量永続化）と duckdb（分析用途）を併用。監視ログは sqlite（monitoring.db）、分析／研究用は duckdb を想定。
- Paper Trading: paper_trading 環境では本番 DB と完全分離されるよう paper_sqlite_path を使用（デフォルト data/paper_trading.db）。
- フェイルセーフ設計: AI API の失敗や DB のスキーマ不足（テーブルがない）などで処理が止まらないよう各所で例外捕捉・フォールバックを導入している。
- テスト・運用: 自動 .env 読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。テストで自動読み込みを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数から読み込み。コード内にベタ書きしない方針。

Acknowledgements
- 各モジュールの実装はアーキテクチャ設計書（PortfolioConstruction.md, StrategyModel.md 等）に基づいており、コメントに設計上の注意点・将来の拡張案を残しています。

その他
- この CHANGELOG はソースコードの内容から推測して作成しています。将来のリリースでは実際の変更箇所に合わせてカテゴリや記述を更新してください。
CHANGELOG
=========

すべての重要な変更は本ファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

- リリース方針: 主要な機能追加は Added、互換性のある変更は Changed、バグ修正は Fixed に記載します。
- 日付はリリース日（YYYY-MM-DD）を示します。

[Unreleased]
------------

追加・改善中の点（現 HEAD に相当、将来リリースで安定化予定）:

Added
- 環境変数の自動読み込み機能を強化
  - プロジェクトルート（.git / pyproject.toml）から .env/.env.local を自動検出して読み込む仕組みを追加。
  - export KEY=val 形式やクォートされた値、インラインコメント、エスケープを考慮したパーサを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - OS 環境変数を保護する protected オプションを導入（.env.local で OS 環境変数を誤って上書きしない）。

- 設定管理（Settings クラス）の強化
  - KABUSYS_ENV / LOG_LEVEL 等の値検証を追加（不正な値は例外）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - paper_trading 用 SQLite パス、pid/kill フラグ等の取得プロパティを追加。

- 実行ユーティリティ
  - set_process_priority, set_cpu_affinity を追加してプロセス優先度と CPU affinity をクロスプラットフォームで設定可能に（Windows / POSIX 対応、失敗時は警告を出力してスキップ）。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading 環境時は MockBrokerClient と専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する意図を明記。

- ポートフォリオ構成
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定 (select_candidates)、等配分/スコア加重 (calc_equal_weights / calc_score_weights)。
    - risk_adjustment: セクター上限の適用 (apply_sector_cap)、マーケットレジームに応じた乗数 (calc_regime_multiplier)。
    - position_sizing: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の allocation_method、lot_size、コストバッファ、aggregate cap のスケールダウン等を実装。

- リサーチ（ファクター計算・特徴量探索）
  - research モジュールを追加:
    - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB の prices_daily / raw_financials を参照して計算）。
    - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank（同順位は平均ランク）。
  - DuckDB 接続を受け取り SQL と Python を組み合わせて高速に処理する設計。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py を追加し、raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントをスコアリングし ai_scores に書き込む機能を実装。
  - バッチ処理（最大 20 銘柄/コール）、記事・文字数トリム、429/ネットワーク/5xx のリトライ（指数バックオフ）やレスポンス検証、スコアの ±1.0 クリップ、部分書き換えによる安全な DB 更新戦略を実装。
  - OPENAI_API_KEY が未設定の場合は ValueError を発生させる。

- 運用支援ツール
  - tools/paper_verification_report.py を追加。paper_trading の SQLite DB を参照して稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出・判定（閾値はソース内で定義）。コマンドラインオプションで日付範囲と DB パスを指定可能。

Changed
- DuckDB / SQLite をデータ取得とモニタリングで併用する設計に整備（duckdb は分析、sqlite はトランザクション・監視ログ用）。
- ExecutionEngine の起動フローを整理（ブローカ生成、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててから run_session を呼び出す）。
- 設定読み込みの優先順位を OS 環境 > .env.local > .env に明示化。

Fixed
- 環境変数 MONITOR_POLL_INTERVAL の不正（0以下・非数）入力時にデフォルトにフォールバックするバリデーションを追加（time.sleep に渡す無効値を回避）。

Notes / Todo
- position_sizing.apply_sector_cap: 価格欠損時のエクスポージャー過少見積りに関する TODO（前日終値や取得原価でのフォールバックを検討）。
- position_sizing: 将来的に銘柄毎の lot_size をサポートする予定。
- DuckDB の executemany に関する注意（空パラメータを渡さないチェックを行う実装指針がある）。

----------------------------------------------------------------

[0.1.0] - 2026-04-13
--------------------

初回リリース — 基本機能セットを公開。

Added
- コア: KabuSys パッケージ初版を追加（__version__ = "0.1.0"）。
- 実行環境 / エントリポイント:
  - run_execution.py: 実運用 / paper_trading を切り替えて ExecutionEngine を起動するスクリプト。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）。
- 設定管理:
  - Settings クラスで環境変数の集中管理を実装。KABUSYS_ENV（development/paper_trading/live）やログレベル等の検証を行う。
  - 自動 .env/.env.local 読み込み（プロジェクトルート検出、読み込み順、上書きルール）。
- データ層:
  - SQLite（監視・トランザクションログ等）と DuckDB（時系列解析・ファクター計算）を併用する設計を導入。初期化ユーティリティ（init_monitoring_db）呼び出しを組み込む。
- 実行コンポーネント:
  - BrokerClientFactory 設計を想定してブローカクライアント抽象化（paper_trading 用 Mock クライアント等）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の起動パイプラインを確立。
- ポートフォリオ構築:
  - 候補選定、等配分・スコア配分、リスクベースのポジションサイジング、セクター上限、レジーム乗数を含む純粋関数群を提供。
- リサーチ:
  - モメンタム・ボラティリティ・バリュー系ファクター計算（DuckDB SQL ベース）。
  - 将来リターン計算、IC 計算、ファクター統計サマリーユーティリティを提供。
- AI / NLP:
  - OpenAI を使ったニュースセンチメントスコアリング機能（バッチ・リトライ・レスポンス検証・DB 書き換えの安全対策を含む）。
- ツール:
  - paper_verification_report: Paper Trading 検証レポート生成 CLI（稼働率、注文成功率、送信率、レイテンシ指標など）。
- ユーティリティ:
  - プロセス優先度設定・CPU affinity ユーティリティ（psutil ベース、クロスプラットフォーム対応、権限不足時に警告）。

Changed
- 主要コンポーネントの責務を分離し、分析（DuckDB）と監視/ログ（SQLite）を明確に分けたデータフローに整理。

Fixed
- 環境変数の不正値に対する耐性を向上（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE 等の検証追加）。
- DB コネクションを finally ブロックで確実にクローズするように整理（run_execution / run_monitoring）。

Security
- OpenAI API キーは引数もしくは環境変数で提供する設計にし、未設定時は明示的にエラーを出す（誤用による無自覚な外部コールを防止）。

Deprecated
- なし

Removed
- なし

Known issues / 注意事項
- news_nlp.score_news は OpenAI API を使用するため、API のレスポンス形式・レート制限に依存する。429 や 5xx を考慮したリトライは実装済みだが、長時間の遅延や API ポリシー変更に注意。
- 一部の計算（MA200 や ATR 等）は十分な過去データがない場合に None を返す設計。上位層での None 処理が必要。
- position_sizing 等のロジックは現状で単元株 100 を前提としており、将来的に株ごとの単元対応が必要。

----------------------------------------
（注）この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や意図した変更区分と異なる可能性があります。リリースに合わせて内容を調整してください。
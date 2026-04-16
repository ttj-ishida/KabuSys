CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — and this file is
maintained in Japanese.

フォーマット
-----------
- バージョン見出しは semantic versioning に従います（例: 1.2.3）。
- 各バージョンは Added / Changed / Fixed / Deprecated / Removed / Security のいずれかのセクションで整理します。

Unreleased
----------
（このセクションは次回リリースまで使用します）

0.1.0 - 2026-04-16
-----------------

Added
- 基本機能の初回リリース。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、MockBrokerClient を通じて本番 DB と分離して実行可能に。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag によるフラグ検出で行う。
  - 両スクリプトとも起動直後にプロセス優先度を設定（set_process_priority("high")）し、duckdb と sqlite の接続を統合的に扱う。
- 環境設定・ロード
  - config.py: 環境変数管理クラス Settings を実装。.env / .env.local の自動読み込み（プロジェクトルート自動検出）、読み込みの上書き制御、OS 環境変数の保護（protected keys）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーを実装し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings に多数のプロパティを追加: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE API 関連、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE（値検証あり）、PAPER_TRADING_SQLITE_PATH、PID / KILL フラグ関連、監視閾値（CPU/MEM/DISK）、環境判定プロパティ（is_live/is_paper/is_dev）、LOG_LEVEL 検証など。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブル存在を保証（冪等）。
- ポートフォリオ構築モジュール
  - kabusys.portfolio.portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
  - kabusys.portfolio.risk_adjustment: セクター集中上限を適用する apply_sector_cap、および市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知はフォールバック）を実装。
  - kabusys.portfolio.position_sizing: position size（発注株数）計算ロジックを実装。risk_based / equal / score の割当方式、単元株（lot）丸め、per-stock 上限・aggregate キャップ（available_cash） のスケーリング、cost_buffer（スリッページ/手数料考慮）や lot 単位での残差処理を含む。
  - portfolio パッケージ __all__ を整備。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度設定（Windows/HIGH/normal/low／POSIX の nice）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足時や未対応プラットフォームは警告してスキップするフェイルセーフあり。
- 研究用モジュール（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value のファクター計算を実装。prices_daily / raw_financials を使用して、MA200 乖離、ATR20、平均売買代金、PER/ROE 等を算出。
  - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（スピアマン）計算(calc_ic)、ランク付け(rank)、ファクター統計サマリー(factor_summary) を実装。外部ライブラリに依存せず標準ライブラリで完結する設計。
- AI ニュース NLP（下書き）
  - ai.news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込むフローを実装。処理ウィンドウ計算(calc_news_window)、バッチ送信（銘柄あたり最大記事数／文字数制限）、最大 20 銘柄バッチ、リトライ（429/ネットワーク/5xx 用の指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）などの設計を導入。score_news 関数は API キー解決とウィンドウ計算を実装（ファイルの一部で実装途中から切れているが主要設計を含む）。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を使って paper_trading DB から
    - システム稼働率（system_status）
    - 注文成功率 / 送信率（trade_logs）
    - リスク却下数（risk_logs）
    - レイテンシ指標（avg/max/P95）
    を集計し、閾値（稼働率/成功率/送信率/P95 レイテンシ）に基づく PASS/FAIL 判定を行う。コマンドライン引数で期間指定 (--from/--to) と DB パス指定 (--db) が可能。
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- 設定ロードの優先順位を明文化: OS 環境変数 > .env.local > .env。読み込み時の上書き挙動と protected キーの取り扱いを改善。
- .env パーサーの堅牢化: export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善、無効行は無視。
- calc_score_weights のフォールバック（全スコア 0 の場合に等金額配分）とログ出力による通知を追加して安全性を向上。
- factor_research / feature_exploration の SQL クエリはスキャン範囲を合理化（必要な範囲のみ）してパフォーマンス配慮を行った。
- position_sizing: aggregate cap のスケーリングと lot 単位での端数処理を導入。残余キャッシュで fractional 残差順に lot を追加配分するロジックを追加。

Fixed
- Settings.paper_fill_mode のバリデーションを導入し、不正な値設定時に早期にエラーを出すようにした（ランタイム設定事故の防止）。
- process_priority の未対応 OS での処理および権限不足時の例外をキャッチして警告に落とすことで、起動失敗のリスクを低減。
- tools.paper_verification_report: DB が存在しない場合のエラーメッセージ出力を明確化。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは score_news の引数または環境変数 OPENAI_API_KEY から取得する仕様にして、未設定時は ValueError を送出して明示的に失敗させることで誤動作を防止。

Notes / 今後の課題
- ai.news_nlp の score_news 実装はファイル末尾で途中切れがあり、完全なバッチ送信 → DB 書込の流れは最終チェック/テストが必要。
- position_sizing の価格欠損（price が 0.0）の扱いは TODO コメントで改善案あり（前日終値や取得原価へのフォールバック等）。
- apply_sector_cap の "unknown" セクターは上限適用をスキップする仕様だが、将来的にデフォルト挙動の見直しが検討される可能性あり。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後の挙動確認や CI 環境での明示的制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）を推奨。

Authors
- このリリースはコードベースから生成された機能群を基にドキュメント化しました。
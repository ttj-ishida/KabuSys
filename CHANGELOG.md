CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- プロジェクト初回リリースとして主要機能を実装。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、MockBroker を用いた完全分離の検証環境をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定・環境変数管理
  - config.py: .env / .env.local の自動読み込み（プロジェクトルート検出）と、環境変数のパース機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - Settings クラスにより環境変数の取得を集中化（DB パス、PID/kill フラグ、閾値、ログレベル、PAPER_FILL_MODE 等）。
- ポートフォリオ構築ロジック
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）と単元株丸め、aggregate cap によるスケーリング処理を実装。スリッページ／手数料バッファ（cost_buffer）を考慮。
- リサーチ機能
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベースの実装）。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリーを実装。外部依存を使わず標準ライブラリで実装。
  - research パッケージの公開 API を定義（zscore_normalize を含む）。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news → 銘柄別集約 → OpenAI（gpt-4o-mini）によるバッチセンチメントスコアリング機能を実装。バッチサイズ、記事／文字数上限、スコア クリップ、リトライ（指数バックオフ）を備える。スコアは ai_scores テーブルへ置換書き込み。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を算出し PASS/FAIL 判定を行う。閾値はソース内の定数で設定可能。
- ユーティリティ
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足時には警告を出し安全にスキップ。
- パッケージ基礎
  - kabusys/__init__.py にバージョン情報（0.1.0）と公開サブパッケージを定義。

Changed
- （初回リリースにつき該当なし）

Fixed
- 環境変数パースの堅牢化: config._parse_env_line がクォート内のエスケープやインラインコメントを正しく扱うように実装。
- run_monitoring.py のポーリング間隔取得において不正値に対するフォールバックを追加（0 以下や非整数入力はデフォルト 60 秒にフォールバックし警告を出力）。
- DB 初期化の冪等性: init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証（複数回呼んでも安全）。

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI API キー取り扱い: news_nlp.score_news は引数 api_key または環境変数 OPENAI_API_KEY を使用し、未設定時は ValueError を送出して不正な呼び出しを防止。

Notes / Known issues / TODO
- position_sizing.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題がコメントで指摘されており、将来的に前日終値や取得原価を用いるフォールバック実装が検討中。
- ai/news_nlp.py:
  - 長い記事を取り扱うためのトリムやチャンク処理、レスポンス検証・部分置換（DELETE→INSERT）等を実装しているが、API レスポンスフォーマットの厳密性に依存するため運用時のモニタリングが推奨される。
- research モジュール:
  - horizons の検証や P95 計算など、データ欠損時は None を返す設計になっているため、呼び出し側での None 処理が必要。
- run_*.py スクリプト:
  - プロセス優先度設定や CPU affinity の適用は権限やプラットフォームに依存し、失敗時は警告ログを出してスキップする安全策を採用。
- 一部のファイル内に TODO / 拡張コメントあり（将来の機能強化候補）。

クレジット
- 本リポジトリの実装はモジュール分割（execution, monitoring, portfolio, research, ai, tools, utils）を意識した設計になっており、ユニットテストや CI、デプロイ用の追加設定は別途整備を推奨します。

もし特定ファイルごとの詳細な変更履歴（関数単位の変更点）や、リリースノートの英語版・箇条書き要約が必要であればお知らせください。
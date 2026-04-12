CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリースを追加。
- 実行エントリ:
  - run_execution.py: 実行エンジン（ExecutionEngine）を起動するスクリプト。KABUSYS_ENV=paper_trading の場合はモックブローカーを用い、Paper Trading 用の SQLite (data/paper_trading.db をデフォルト) を使用する分離が実装されている。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する。
- 設定管理:
  - config.py: .env 自動読み込み機能（プロジェクトルート検出、.env / .env.local の読み込み、OS 環境変数の保護）を実装。Settings クラスで環境変数をラップし、型・有効値チェックを提供。
  - 多数の設定プロパティを追加（DB パス、PID/KILL ファイルパス、しきい値、環境種別判定、PAPER_FILL_MODE など）。
- モニタリング/DB:
  - monitoring_db 初期化呼び出しを run_* スクリプトに組み込み、監視テーブルの存在を保証（冪等）。
  - DuckDB を分析用 DB として使用するための接続ハンドリングを追加（各スクリプトで duckdb.connect を利用）。
- Portfolio コンポーネント（純粋関数群）:
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
  - portfolio.position_sizing: 発注株数計算(calc_position_sizes)。リスクベース／等分配／スコア配分に対応し、単元株丸め、最大ポジション上限、利用可能現金に応じたスケールダウン（aggregate cap）を実装。
  - portfolio.risk_adjustment: セクターキャップ適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier)。
  - portfolio パッケージのエクスポートを整備。
- Research（ファクター・特徴量解析）:
  - research.factor_research: モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) ファクターの DuckDB ベース計算。
  - research.feature_exploration: 将来リターン算出(calc_forward_returns)、IC（Spearman）計算(calc_ic)、rank/統計サマリー(factor_summary) を提供。外部ライブラリに依存せず純粋 Python + DuckDB で実装。
  - research パッケージのエクスポートを整備（zscore_normalize の re-export など）。
- AI ニュース NLP:
  - ai.news_nlp: raw_news から銘柄ごとのセンチメントスコアを OpenAI（gpt-4o-mini）で算出し ai_scores へ書き込む処理を実装。バッチ処理、トークン肥大化対策（記事数・文字数制限）、スコアクリッピング、レスポンスバリデーション、部分成功時の DB 保護（対象コードのみ DELETE/INSERT）を含む。
  - ニュースウィンドウ計算（JST→UTC の変換）を実装。
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定を出力。--from/--to/--db オプションに対応。
- ユーティリティ:
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）、および CPU affinity 設定(set_cpu_affinity)。アクセス権限不足や未対応 OS の場合は警告を出してフォールバック。

Changed
- 設定の堅牢化:
  - config._load_env_file/_parse_env_line: export 前置、クォート処理、インラインコメント処理、保護キー（OS 環境変数）概念を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。
  - Settings クラスでの入力検証を強化（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の有効値チェック）。
- DB 接続と環境分離:
  - run_execution: paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全分離する挙動を明確化。monitoring テーブル初期化は冪等で呼び出す。
  - run_monitoring: 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記（実装上もその通り）。
- ポジションサイジング:
  - calc_position_sizes: lot_size 単位での丸め、max_position_pct に基づく per-stock 上限、aggregate cap のスケールダウンと残差配分アルゴリズムを実装。cost_buffer による保守的なコスト見積りを考慮。
- リスク制御:
  - apply_sector_cap: 既存保有額をセクター別に計算し、max_sector_pct を超えるセクターの候補除外を実装。unknown セクターはキャップの対象外にしている点を明記。
  - calc_regime_multiplier: 未知のレジームは警告して 1.0 でフォールバック。
- Research / Feature 工程:
  - calc_forward_returns: horizons の入力検証、単一クエリで複数ホライズンを取得する最適化、スキャン日数のバッファを導入。
  - calc_ic / rank: ties（同順位）の平均ランク処理、少数サンプルでの None フォールバック、ランク算出で丸めを行い浮動小数点の ties 検出漏れを防止。
- ニュース NLP:
  - score_news: OpenAI クライアントの使い方を抽象化し、バッチ単位（_BATCH_SIZE=20）での送信、API エラー（429, ネットワーク, 5xx）へのリトライ、出力 JSON の厳格検証、スコア範囲クリップを実装。API 未設定時は ValueError を投げる。

Fixed
- 環境変数パースの堅牢化:
  - .env のクォートやエスケープ、コメントの扱いに関する不整合を修正し、より実運用の .env を正しく読み込めるようにした。
- ポーリング間隔の安全化:
  - MONITOR_POLL_INTERVAL の解析で 0 以下や不正値を検出した際にデフォルトにフォールバックし、time.sleep へ渡して例外が発生しないようにした（警告ログ出力）。
- process_priority / cpu_affinity:
  - 未対応プラットフォームや権限不足を考慮して例外を捕捉し、フォールバック（スキップ）する動作を安定化。
- DuckDB 実行の安全化:
  - ai/news_nlp において executemany 前にパラメータが空でないことを確認する等、DuckDB の制約に配慮した実装改善。

Notes / Implementation details
- バージョン: package ルートで __version__ = "0.1.0" を設定。
- 日時の取り扱い:
  - News モジュールやツールはルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない設計方針を採用（一部関数は target_date を明示的に受け取る）。
- フェイルセーフ設計:
  - AI API や外部依存（ブローカー等）が失敗した場合でも、部分的な失敗を許容して他の処理を継続するよう設計されている（ログ出力・スキップ）。
- テスト/運用向けフラグ:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で .env 自動読み込みを無効化可能（テストなどで有用）。
- ドキュメント:
  - 各モジュールに実装意図・注意点・設計方針を記載した docstring を多めに追加している。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で与える必要があり、未設定時はエラーを発生させる設計。
- .env 自動ロード時に OS 環境変数は protected として上書きを防ぐ実装を行っている。

Acknowledgements / Future
- 今後の予定（未実装/検討中）:
  - position_sizing の lot_size を銘柄別にする拡張（stocks マスタに lot_size を持たせる設計）。
  - price 欠損時のフォールバック（前日終値や取得原価）導入。
  - AI レスポンスのより堅牢なスキーマ検証やメトリクス収集の強化。
  - テストカバレッジ強化と CI ワークフロー整備。

---
この CHANGELOG はソースコードから推測して作成しています。実際の開発履歴やコミット履歴と差異がある可能性があるため、正式なリリースノート作成時は Git のコミットログやリリースノートを参照してください。
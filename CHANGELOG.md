# Changelog

すべての重要な変更点をここに記載します。本ドキュメントは Keep a Changelog の形式に準拠しています。  

現在のバージョン: 0.1.0（初期リリース）

---

### [Unreleased]
- なし

---

### [0.1.0] - 2026-04-11

Added
- プロジェクト初回リリース。
- 基本アーキテクチャ・起動スクリプトを追加
  - run_execution.py：ExecutionEngine を起動するスクリプトを追加。実稼働 / ペーパートレード（KABUSYS_ENV=paper_trading）間で SQLite DB を分離して動作（paper_trading は data/paper_trading.db を使用）。プロセス優先度を最初に「high」に設定。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理
  - config.py：環境変数と .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。export 付き行やシングル/ダブルクォート、インラインコメント、.env.local の優先度制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスで多数のプロパティを提供（DB パス・PID/フラグパス・閾値・ログレベル・環境種別判定・PAPER_FILL_MODE のバリデーション等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder：シグナル選定（select_candidates）と等額/スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment：セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing：発注株数算出ロジック（risk_based / equal / score）を実装。lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り等をサポート。
- 実行周りのユーティリティ
  - utils.process_priority：Windows と POSIX（Linux/Mac 等）差分を吸収するプロセス優先度設定と CPU affinity 設定のユーティリティを実装。権限不足や未対応 OS での安全なスキップを備える。
- リサーチ機能
  - research.factor_research：モメンタム／ボラティリティ／バリュー系ファクター計算を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。ma200 乖離・ATR・20日出来高等を計算。
  - research.feature_exploration：将来リターン計算（複数ホライズン）、IC（Spearman）計算、ランク関数、ファクター統計サマリーを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI 関連（LLM 統合）
  - ai.news_nlp：raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を生成・書き込みする機能を実装。JSON Mode の活用、チャンクバッチ（最大 20 銘柄）、トークン肥大化対策、429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ、レスポンス検証、結果の ±1.0 切り捨て、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
  - ai.regime_detector：ETF（1321）の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定し、market_regime テーブルへ冪等書き込みする機能を実装。API 失敗時は安全に macro_sentiment=0.0 を採用して処理継続。
- DB・クエリ関連
  - DuckDB を用いた分析用接続を各モジュールで利用（research / ai 等）。prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等のテーブルを前提に実装。
- ロギング
  - 起動スクリプト等で基本ログレベル INFO をデフォルト設定。内部でデバッグログやワーニングを適宜出力するよう実装。

Changed
- N/A（初回リリースのため既存機能の変更はなし）

Fixed
- DB 書込みや API 呼び出し周りでの安全性を強化
  - ai.news_nlp で DuckDB の executemany が空リストを受け取れない制約に対応するため、空チェックを追加してから executemany を呼び出す実装とした（互換性向上）。
  - API 呼び出し時の例外ハンドリング（RateLimitError / APIConnectionError / APITimeoutError / APIError）を細かく処理し、適切にログとリトライを行うようにした。
- Settings の .env パーサーを強化し、クォート内のバックスラッシュエスケープや export 形式、インラインコメントの扱いを適切に処理するようにした。

Deprecated
- なし

Security
- API キー（OpenAI など）は明示的に引数で与えるか OPENAI_API_KEY 等の環境変数から取得する設計。環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能で、テストや CI 用途での安全性を確保。

Notes / Known limitations / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合に既存コメントで指摘の通りエクスポージャーが過少評価されうる。将来的に前日終値や取得原価でのフォールバックを検討する必要がある。
- position_sizing: 現状 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_size を stocks マスタで持たせる拡張を想定（TODO コメントあり）。
- ai.news_nlp / regime_detector: LLM 呼び出しは外部 API に依存するため、API 料金やレート制限・レスポンス仕様変更に注意。API レスポンスの厳格な JSON 出力を期待しているが、復元ロジックを持つものの完全な保証はない。
- run_monitoring.py は監視 DB に本番 sqlite_path を常に使用する（意図的）。テスト等で別 DB を使いたい場合は設定側で切り替えてください。
- process_priority・set_cpu_affinity は権限不足や未対応環境で安全にスキップする実装だが、実行環境の権限に依存する。

Version
- パッケージバージョンは kabusys.__version__ = "0.1.0"

---

開発・運用に関する詳細（設計メモや仕様）は各モジュールの docstring / コメントを参照してください。変更履歴は今後のコミットで Unreleased に追記し、リリース時にバージョンセクションを追加していく予定です。
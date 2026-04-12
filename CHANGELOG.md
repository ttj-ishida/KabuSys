# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリース日: 2026-04-12

## [0.1.0] - 2026-04-12

### Added
- 初回リリース: KabuSys 0.1.0 を公開。
- 実行 / 監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続してエンジンを起動します。Paper Trading 環境 (`KABUSYS_ENV=paper_trading`) では MockBrokerClient を利用し、専用の paper_trading DB に書き込む設計です。
  - run_monitoring.py: SystemMonitor をポーリングで起動するスクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
- 設定管理モジュール（kabusys.config）を追加
  - .env 自動ロード機能（プロジェクトルートを自動検出: .git / pyproject.toml）。
  - .env パーサを独自実装。`export KEY=val`、引用符付き値（バックスラッシュエスケープ対応）、インラインコメント処理をサポート。
  - 環境変数自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 設定値取得用 `Settings` クラスを追加（各種パス、API トークン、閾値、フラグなど）。
  - `PAPER_FILL_MODE` の検証（許容値: `"instant"|"partial"|"never"|"reject"`）を実装。
- 監視関連
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼出してテーブル存在を保証（冪等）。
  - 監視スクリプトは環境に関わらず本番の `sqlite_path` を使う（監視は本番 DB を参照する仕様）。
- Execution 系コンポーネント
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager といった実行系コンポーネントを組み合わせる起動フローを追加。
  - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。初期 portfolio value はブローカーの利用可能現金から取得。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 銘柄選定: select_candidates（スコア降順・タイブレークロジック）
  - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）
  - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）
  - 版サイズ算出: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）
- 研究・ファクター計算（kabusys.research）
  - ファクター群: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL ベースの実装）
  - 特徴量探索: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank
  - zscore_normalize をエクスポート（kabusys.data.stats から）
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）へ一括リクエストし、銘柄ごとのセンチメントを ai_scores に書き込む処理を追加。
  - バッチサイズ、トークン対策（記事数・文字数制限）、最大リトライ、指数バックオフ、レスポンス検証、スコアクリップ（±1.0）などの堅牢化。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を実装（JST ベースの仕様を UTC に変換）。
- ツール
  - paper_verification_report: Paper Trading 検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計・判定し標準出力に表示。コマンドラインオプションで期間指定と DB パス指定が可能。
- ユーティリティ
  - process_priority: プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定を追加（psutil を利用、失敗時は警告でスキップ）。

### Changed
- 起動時のプロセス優先度設定を各起動スクリプトの最初に実行するように統一（`set_process_priority("high")`）。
- run_execution は paper_trading 環境において production DB と完全に分離された SQLite パス（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用するようにした。
- 監視用 DB 初期化（init_monitoring_db）は冪等に呼び出されることを明示。
- 各種モジュールで DuckDB / SQLite 接続を受け取る設計に統一し、DB 参照部分とビジネスロジックの分離を意識した実装に変更。

### Fixed
- .env の読み込み/パースに関する改善
  - `export KEY=val` 形式に対応。
  - 引用符付き値のバックスラッシュエスケープを正しく処理。
  - 引用符なし値のインラインコメント判定（直前がスペース/タブである場合にコメント扱い）を導入。
  - OS 側の環境変数を保護するため、既存 OS 環境変数は上書きしない機能（protected keys）を実装。
- process_priority / set_cpu_affinity 実行時に権限不足や未実装 API に遭遇しても例外を握りつぶして警告ログにフォールバックするようにして、起動失敗を防止。
- paper_verification_report
  - P95 算出ロジックを実装（空リストは None を返す）。
  - DB が存在しない場合のユーザーフレンドリーなエラーメッセージを追加。
  - 日付フィルタ・SQL の堅牢化（存在しないテーブルに対する OperationalError を捕捉してデフォルト値で扱う）。
- research / feature_exploration の入力検証（horizons の範囲チェックなど）を追加。

### Security
- AI スコア生成 (news_nlp.score_news) は OpenAI API キーの未設定時に明確に ValueError を投げるようにし、キーの取り扱いを明示（環境変数 `OPENAI_API_KEY`、または関数引数）。

### Notes / Migration
- 新規環境では .env をプロジェクトルートに配置すると自動で読み込まれます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視エージェントは常に（環境に関係なく）`Settings.sqlite_path` を使用します。監視データを別 DB に分けたい場合は設定ファイル側でパスを変更してください。
- 環境変数の追加 / 変更（主なもの）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。不正値はデフォルト 60 秒にフォールバックして警告。
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（run_execution の paper_trading 用 DB）。
  - PAPER_FILL_MODE: Paper Trading の fill 動作モード。許容値は "instant" / "partial" / "never" / "reject"。不正値は起動時に例外。
  - OPENAI_API_KEY: ai/news_nlp.score_news を実行する際に必要。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するフラグ（任意）。
- DuckDB の一括書き込み前にパラメータが空でないことを保証する必要がある点に注意（実装ドキュメントに言及あり）。

### Removed
- （初回リリースのため該当なし）

--- 

今後のリリースでは、運用で得られたフィードバックに基づき以下を検討しています（予定）
- position_sizing の銘柄別 lot_size サポート（stocks マスタの導入）。
- apply_sector_cap の price フォールバック戦略（前日終値や取得原価の利用）。
- AI モジュールのロギング強化と部分失敗時の局所リトライ/ロールバック戦略の改善。
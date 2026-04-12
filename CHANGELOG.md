CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトのバージョンはパッケージ定義（kabusys.__version__）に従って管理しています。

フォーマット:
- 変更は "Added", "Changed", "Fixed", "Removed", "Security" のセクションで分類しています。
- 日付はリリース日を示します。

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-12
--------------------

Added
- 初期リリースとして基本機能を実装。
- 実行起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（Settings を参照）。プロセス優先度を起動時に設定し、duckdb/SQLite 接続を扱う。
  - run_monitoring.py: SystemMonitor をポーリングする常駐スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config.py: .env / .env.local の自動読み込み機構を導入（プロジェクトルートの探索 .git / pyproject.toml を基準）。環境変数読み込み時に OS 環境変数を保護する挙動を実装。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、PID/KILL ファイルパス、環境判定など）をプロパティとして安全に取得できるようにした。
  - PAPER_FILL_MODE の入力検証を追加（"instant"|"partial"|"never"|"reject" のみ許容）。
- モニタリング
  - monitoring_db 初期化処理を用意（init_monitoring_db 呼び出し）。run_monitoring は環境に関わらず本番 sqlite_path を使用する旨を仕様化（監視側は本番 DB を見る想定）。
- Execution コンポーネント（実行系）
  - ブローカークライアントのファクトリ（BrokerClientFactory）や ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てと起動フローを実装。
  - RiskConfig によるリスク制約（max_position_pct, max_utilization, rate_limit 等）を標準設定として採用し、初期ポートフォリオ値はブローカーの利用可能現金に基づいて設定。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。score_weights は全スコアが 0 の場合に等金額にフォールバック。
  - position_sizing: 発注株数計算（risk_based / equal / score）を実装。lot_size による丸め、単銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）をサポート。cost_buffer によるコスト見積りも考慮。
  - risk_adjustment: セクター集中上限のチェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- リサーチ機能（kabusys.research）
  - factor_research: モメンタム（1/3/6 か月リターン、MA200 乖離）、ボラティリティ（ATR20、出来高指標）、バリュー（PER/ROE）等のファクター計算関数を実装。DuckDB を用いた SQL ベースの集計を採用。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ランクに基づく IC（calc_ic）、ファクターの統計サマリ（factor_summary）、ランク化ユーティリティ（rank）を実装。外部依存（pandas 等）なしで標準ライブラリのみで実装。
  - research モジュールの public API を整理してエクスポート。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントスコアを生成し、ai_scores テーブルへ書き込む処理を実装。バッチ・チャンク処理、レスポンス検証、スコアクリップ（±1.0）、リトライ（指数バックオフ）等を備える。ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足や未サポート環境では警告を出してスキップするフェイルセーフあり。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 形式で出力。コマンドライン引数で期間指定可能。

Changed
- 初期設計段階として、DuckDB と SQLite を併用するデータアクセスパターンを明確化（DuckDB は分析用、SQLite は監視・注文ログ用など）。
- .env 読み込み順序を OS 環境 > .env.local > .env と定義し、環境からの上書きを保護する仕組みを導入。

Fixed
- .env パーサーの改善:
  - export KEY=val 形式を許容。
  - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
  - クォート無しの場合のインラインコメント処理の振る舞いを改善（'#' の直前に空白がある場合のみコメントとみなす）。
  - 不正行に対する堅牢性を向上。
- run_monitoring の MONITOR_POLL_INTERVAL のパースで 0 以下や不正値が指定された場合にデフォルトへフォールバックする処理を追加し、time.sleep に渡せない値を回避。

Security
- 本リリースでは特定のセキュリティ修正はありません。API キーやパスワード等の取得は環境変数経由とし、Settings._require によって未設定時に明示的にエラーを出すことで安全性を高めています。

Removed
- 該当なし（初期リリース）

Notes / Breaking changes / Warnings
- 監視プロセス（run_monitoring）は「環境（KABUSYS_ENV）」に関わらず本番用の sqlite_path を参照する挙動がドキュメント化されています。運用時は監視 DB の参照先に注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB とは完全に分離された PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用するよう設計されています。テスト/検証時は DB パスを明示的に設定してください。
- PAPER_FILL_MODE の値チェックが厳密になったため、環境変数の値が想定外の場合は起動時に ValueError を送出します。
- process_priority / cpu_affinity の設定は権限や OS に依存します。権限不足時は警告を出してスキップします。

今後の予定（例）
- ニュース NLP のロバスト性向上（部分失敗時のロールバック戦略やより詳細なレスポンス検証）。
- 銘柄別 lot_size の対応（現状はグローバルな単元株数を想定）。
- DuckDB のスキーママイグレーション管理・テスト用データセット導入。

----
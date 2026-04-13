CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
（https://keepachangelog.com/ja/）

すべての重要な変更をこのファイルに記録してください。
バージョン番号は semver に従います。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- プロジェクト初期リリース。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、ExecutionEngine のセッション実行を行う。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
- 環境設定管理（kabusys.config）を実装:
  - .env/.env.local 自動読み込み（プロジェクトルート検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 複雑な .env 行パーサ（export 形式、クォート／エスケープ、インラインコメント処理）。
  - Settings クラス: 環境変数取得ラッパー（バリデーション付き）。各種パス・フラグ、閾値、PAPER_FILL_MODE 等の検証を提供。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加:
  - portfolio_builder: シグナル選定（select_candidates）、等金額／スコア重み計算（calc_equal_weights, calc_score_weights）。
  - position_sizing: position サイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンロジック、コストバッファ対応。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
- 研究／分析モジュールを追加（kabusys.research）:
  - factor_research: momentum / volatility / value ファクター計算（DuckDB を用いた SQL 実装）。200 日移動平均・ATR 等の算出を含む。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、スピアマンランク相関による IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）等。
  - research.__init__ で主要関数を公開。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）:
  - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores に書き込む処理を実装。
  - バッチサイズ、トークン肥大対策（記事数／文字数トリム）、429/5xx/ネットワークの指数バックオフリトライ、レスポンス検証、スコアクリップをサポート。
  - ニュース収集ウィンドウ計算ユーティリティ（JST→UTC 変換）を実装。
- ユーティリティを追加:
  - process_priority: プラットフォーム間の差を吸収するプロセス優先度設定および CPU affinity 設定。Windows/POSIX を考慮し、権限不足や未対応環境では警告を出して安全にスキップ。
- monitoring / tools:
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）使用を想定した実行スクリプト統合。
  - tools/paper_verification_report: Paper Trading 用 SQLite DB を解析して検証レポートを標準出力に出すスクリプト。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標と閾値判定を提供。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で解決。未設定時は ValueError を発生させて誤った公開を防止。

Notes / その他の設計上の注意
- run_monitoring は監視用 DB として常に Settings.sqlite_path を使用する設計（環境に依らず本番の監視 DB を対象）。
- run_execution は paper_trading 環境用に paper_sqlite_path を分離しているため、paper 環境での検証は本番 DB に影響しない。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に探索するため、CWD に依存しない。
- 各種計算関数（ポートフォリオ構築、ファクター計算、特徴量解析）は副作用を持たない純粋関数として設計され、DB 参照／計算範囲が明確に分離されている。

開発者へ
- 将来的に stocks マスタに単元情報を持たせ、銘柄別 lot_size を受け取る拡張を想定（position_sizing の TODO）。
- apply_sector_cap の露出計算は price が欠損（0.0）の場合に過少見積もりになる点が注記されており、価格フォールバックの実装が検討対象。
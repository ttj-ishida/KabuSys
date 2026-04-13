Keep a Changelog
=================

すべての重要な変更点はこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

注: 以下の履歴は提供されたソースコードの内容から推測して作成した初期リリースおよび主要機能の一覧です。

[Unreleased]
------------

- 今後の変更をここに記載します。

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース。KabuSys の基本モジュール群を追加。
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定し、環境に応じて本番/ペーパー用 SQLite を選択して接続、DuckDB も接続してセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
- 設定/環境変数管理
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）、読み込み優先度 OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。多数の設定プロパティ（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE の検証など）を提供。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選択（スコア降順＋タイブレーク）、等金額・スコア加重の重み計算を追加。スコア全てがゼロの場合は等金額にフォールバック（警告）。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）を追加。単元株（lot_size）丸め、per-position と aggregate の上限、cost_buffer を考慮したスケールダウンアルゴリズムを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバック値に警告を出す。
- リサーチ/ファクター計算
  - research/factor_research.py: Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR、平均売買代金、出来高比率）、Value（PER, ROE）ファクターを DuckDB 上で計算する関数を実装。欠損・データ不足時の扱いを明示。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリ非依存（標準ライブラリのみ）。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント化して ai_scores テーブルに書き込む機能を実装。処理は銘柄ごとに記事を集約し、最大 20 銘柄ずつバッチ送信。429/ネットワーク/5xx 等は指数バックオフでリトライ。レスポンス形式の厳格なバリデーションとスコアの ±1.0 クリップを行う。API キーは引数または環境変数 OPENAI_API_KEY から取得。
  - calc_news_window: target_date に対するニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を正確に算出。
- ユーティリティ
  - utils/process_priority.py: Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は警告を出して安全にスキップする。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。P95 計算、日付フィルタ、DB 存在チェック、デフォルト DB パス（data/paper_trading.db）対応。
- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を用いて、監視テーブル群の初期化を起動時に行う（冪等）。
- パッケージ情報
  - __init__.py によるバージョン設定 __version__ = "0.1.0" と公開 API の __all__ 定義。

Changed
- なし（初回リリースのため）。

Fixed
- いくつかの堅牢性・境界ケース対応を実装（コード内の defensive checks）
  - config._parse_env_line: .env パースでクォートやエスケープ、インラインコメント判定を慎重に扱う実装。
  - portfolio/position_sizing.calc_position_sizes: 価格未取得（None/0）時のスキップ、aggregate cap スケールダウン時の再配分ロジック、lot_size による丸め、安全弁を設定。
  - research/feature_exploration.calc_ic: データ不足（有効レコード < 3）や分散 0 の場合に None を返す。
  - tools/paper_verification_report: DB のテーブルが存在しない場合に sqlite3.OperationalError を捕捉してフォールバックする実装。
  - utils/process_priority: 未対応 OS や権限エラー時に警告を出して処理を継続する。

Security
- 外部 API キー（OpenAI）は環境変数または明示的引数でのみ受け取り、未設定時は ValueError を送出することでキー漏洩や誤設定を緩和。

Notes / Known behaviors
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視用 DB は本番と共通）。run_execution は paper_trading 環境では paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離する。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ有効。無効値は起動時にエラーとなる。
- .env 自動読み込みはプロジェクトルートが特定できた場合にのみ行われ、OS 環境変数は既定で保護される（.env の上書き防止）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- AI スコアリングはバッチ単位（最大 20 銘柄）で API コール、記事・文字数でトークン肥大を抑えるための上限を設けている（記事数・文字数トリム）。

作者
- ソースコード内の実装に基づき推測して作成。

今後の予定（候補）
- 単元ごとの lot_size を銘柄別にサポートする拡張（stocks マスタからの取得）。
- position_sizing のコスト推定・slippage モデルの改善（手数料/スリッページのより厳密な扱い）。
- ai/news_nlp の失敗時の部分ロールバック/部分再試行戦略、より細かなエラーハンドリング。
- DuckDB を用いる分析部分の最適化・並列化。

--- 

（この CHANGELOG は提供されたソースコードから機能・仕様を推測して作成しています。実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。）
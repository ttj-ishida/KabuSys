CHANGELOG
=========

すべての注目すべき変更はここに記載します。フォーマットは "Keep a Changelog" に準拠します。
タグ付けやリリース日付はリポジトリの実際の運用に合わせて追記してください。

[Unreleased]
-------------

- なし（最新の安定版は 0.1.0 を参照してください）。

0.1.0 - 初回公開
----------------

追加（Added）
- 実行エントリ / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を設定し、SQLite/DuckDB 接続の初期化を行う。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとセッション実行。

- 設定管理
  - config.py: .env 自動読み込み機構と Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（OS 環境変数優先、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に耐性あり。
    - Settings に多数のプロパティを用意（J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定 等）。
    - PAPER_FILL_MODE の値検証（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev の補助プロパティを追加。

- 監視関連
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 日付フィルタ（--from / --to）対応、DB パスはオプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等の指標を集計し、閾値（デフォルト）に基づいて PASS/FAIL 判定を出力。
    - P95 計算、NULL 考慮、テーブル欠如時のフォールバックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックし WARN ログを出力。
  - portfolio.risk_adjustment: セクター上限フィルタ（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - セクター未登録 ("unknown") は上限適用外、既存ポジション評価時に売却予定銘柄を除外可能。
    - 未知レジームは 1.0 にフォールバックして警告ログ。
  - portfolio.position_sizing: 株数（shares）決定ロジックを実装（risk_based / equal / score の各方式）。
    - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積り等を実装。
    - lot_size（現在デフォルト 100）に基づく端数処理、残余キャッシュでの再配分ロジックを持つ。

- 研究（Research）機能
  - research.factor_research: モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）ファクター計算を追加。
    - DuckDB の prices_daily / raw_financials を参照して、営業日ベースのウィンドウ処理や窓関数を用いた計算を行う。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）／ランク（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず純粋な Python + DuckDB SQL で実装。
  - research.__init__ で zscore_normalize（data.stats 経由）等のエクスポートを整理。

- AI / NLP
  - ai.news_nlp: raw_news の記事を OpenAI（gpt-4o-mini）でバッチセンチメントスコアリングし ai_scores に書き込む処理を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に定義し、記事を銘柄ごとに集約して一定の文字数・記事数でトリムする。
    - バッチサイズ制御（最大 20 銘柄/コール）、429/タイムアウト/5xx 等に対する指数バックオフリトライ、レスポンス構造のバリデーション、スコアの ±1.0 クリップ、部分成功時の保護（対象コードのみ置換）などフェイルセーフを重視した実装。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ユーティリティ
  - utils.process_priority: プラットフォームを吸収するプロセス優先度設定ユーティリティを追加。
    - Windows/Linux/Mac/FreeBSD に対応（psutil に依存）。set_process_priority("high"|"normal"|"low")、set_cpu_affinity によるコア固定機能を提供。
    - 未対応 OS や権限不足時は警告を出して安全にスキップ。

変更（Changed）
- パッケージ初期化
  - kabusys.__init__ に __version__ = "0.1.0" を追加。
  - portfolio / research モジュールでの関数エクスポートを整理し、外部からの利用を簡潔にした。

不具合修正（Fixed）
- run_monitoring のポーリング間隔取得で不正な値（0 以下や非整数）を検出した場合にデフォルトへフォールバックし warn を出すようにして、time.sleep に渡す不正値による例外発生を回避。

注意事項 / Breaking Changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず "本番" の sqlite_path を使用します。開発や paper_trading 環境で監視用 DB を分離したい場合は環境変数 SQLITE_PATH を明示的に設定してください。
- config の自動 .env 読み込みは OS 環境変数を保護（上書き不可）します。CI やテストで意図的に .env を完全に適用したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効にし、明示的にロードする運用にしてください。
- PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の不正値は起動時に ValueError を送出します。環境変数値はリリース前に確認してください。
- ai.news_nlp は OpenAI API を利用するため、API キー（OPENAI_API_KEY）や利用料金、レート制限に注意してください。API 呼び出し失敗時は一部スコアを取得できない可能性があるため、部分的な結果での置換処理を設計上行っています。

既知の改善余地（今後の候補）
- position_sizing: 銘柄ごとの lot_size を stocks マスタで管理する拡張（現在はグローバル lot_size）。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価）でエクスポージャー過少見積りを回避する改善。
- ai.news_nlp: OpenAI のレスポンス JSON の堅牢なスキーマ検証強化、処理の非同期化や並列化によるスループット向上。
- process_priority: container 環境や特権が限定された環境での挙動向上（追加の権限チェックやより緻密なフォールバック）。

-- END --